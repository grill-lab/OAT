import torch

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from taskmap_pb2 import OutputInteraction, Image, ScreenInteraction, Video, TaskMap, ExtraInfo, ExecutionStep
from .abstract_step_augmenter import AbstractBatchStepAugmenter


class SummaryAugmenter(AbstractBatchStepAugmenter):

    def __init__(self):
        super().__init__()
        self.model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")
        self.tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
        self.prompt = 'In a few sentences, can you summarize the main points of the input text?'
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def condition(self, step: ExecutionStep) -> bool:
        if step.response.speech_text > 700:
            return True
        else:
            return False

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

    def batch_process(self, batch):
        input_list = []
        hash_list = []
        for (hashval, step, _) in batch:
            step_text = step.response.screen.paragraphs[0]
            text = f"Summarize: {step_text}"
            input_list.append(step_text)
            hash_list.append(hashval)
        with torch.no_grad():
            inputs = self.tokenizer(input_list, return_tensors='pt', padding=True,
                                    max_length=512, truncation=True).to(self.device)
            output_ids = self.model.generate(input_ids=inputs.input_ids, attention_mask=inputs.attention_mask)
            generated_summaries = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)
            return generated_summaries
