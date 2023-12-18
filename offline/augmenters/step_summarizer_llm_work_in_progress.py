from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub

class StepSummarizerLMM(AbstractSimpleStepAugmenter):

    def __init__(self):
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(neural_channel)
    
    def condition(self, step: ExecutionStep) -> bool:
        text_split = step.response.screen.paragraphs[0]
        return len(text_split) > 30

    def apply_output(self, original_step: ExecutionStep, generated_summary: str) -> ExecutionStep:

        step_text = original_step.response.screen.paragraphs[0]
        del original_step.response.screen.paragraphs[:]

        screen = ScreenInteraction()
        screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
        screen.paragraphs.append(generated_summary)

        original_step.response.screen.MergeFrom(screen)
        original_step.response.description = step_text
        original_step.response.speech_text = generated_summary

        return original_step    

    def get_transformed_input(self, taskmap: TaskMap):
        return None
    
    @staticmethod
    def summarize_text(step_text):
        model_request: ModelRequest = ModelRequest()
        prompt = f"Summarize this paragraph in less than three sentences: \n {step_text}"
        model_request.formatted_prompt = prompt
        model_request.max_tokens = 50       
        generated_sample = self.llm.call_model(model_request)
        return generated_sample

    def batch_process(self, batch):
        paragraphs = []
        for (hashval, step, _) in batch:
            step_text = step.response.screen.paragraphs[0]
            text = f"Summarize: {step_text}"
            paragraphs.append(step_text)
        
        generated_summaries = []
        for paragraph in paragraphs:
            generated_sample = self.summarize_text(paragraph)
            generated_summaries.append(generated_sample)
        
        return generated_summaries