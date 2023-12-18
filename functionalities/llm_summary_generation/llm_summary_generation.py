import grpc
import os
import re

from compiled_protobufs.llm_pb2 import ModelRequest, ModelResponse, SummaryGenerationRequest, SummaryGenerationResponse, \
    ModelBatchRequest, SummaryGenerationRequest, MultipleSummaryGenerationRequest, MultipleSummaryGenerationResponse
from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub

from utils import logger


def process_response_text(response_text: str) -> str:
    # remove whitespace
    text = ' '.join(response_text.split("\n"))
    if not re.search(r'[.!?]', text[-1]):
        # If not, add a period (.) to the end of the text
        text += '.'

    # split at punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    complete_sentences = []
    for sentence in sentences:
        if sentence.endswith(('.', '!', '?')):
            # remove numbered lists
            sentence = re.sub(r'\d+\.', '', sentence)
            complete_sentences.append(sentence.strip())
    return ' '.join(complete_sentences)


def truncate_details(details: str) -> str:
    details_list = details.split(" ")
    n = min(100, len(details_list))
    return " ".join(details_list[:n])


def extract_qa_answer(generated_answer):
    start_token = "### Response:"
    end_token = "#"
    if start_token in generated_answer:
        generated_answer = generated_answer.split(start_token)[1]
    if end_token in generated_answer:
        generated_answer = generated_answer.split(end_token)[0]
    generated_answer = generated_answer.replace('\n', " ")
    if ". " in generated_answer:
        generated_answer = ". ".join(generated_answer.split('.')[:-1])
    return generated_answer.strip()


class LLMSummaryGeneration:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)

    def generate_summary(self, request: SummaryGenerationRequest) -> SummaryGenerationResponse:
        model_request: ModelRequest = ModelRequest()

        step_text = request.step_text
        title = request.task_title
        details = request.more_details
        details = truncate_details(details)
        summary_generation_prompt = "Create a brief 2-sentence text by condensing key points from both the Details " \
                                    "and the Step, omitting insignificant details."

        model_input = f"""Below is an instruction that describes a task, paired with an input that provides further 
        context. Write a response that appropriately completes the request.

        ### Instruction:
        {summary_generation_prompt}

        ### Input:
        Task title:  {title}

        Step: {step_text}

        Details: {details}

        ### Response:
        """

        model_request.formatted_prompt = model_input
        model_request.max_tokens = 100

        llm_response = self.llm.call_model(model_request)

        summary_response: SummaryGenerationResponse = SummaryGenerationResponse()
        summary_response.summary = process_response_text(extract_qa_answer(llm_response.text))
        return summary_response

    def generate_summaries(self, request: MultipleSummaryGenerationRequest) -> MultipleSummaryGenerationResponse:
        model_batch_request: ModelBatchRequest = ModelBatchRequest()
        model_batch_request.max_tokens = 100

        summary_generation_prompt = "Create a brief 2-sentence text by condensing key points from both the Details " \
                                    "and the Step, omitting insignificant details."

        for title, step, details in zip(request.task_title, request.step_text, request.more_details):
            model_input = f"""Below is an instruction that describes a task, paired with an input that provides 
            further context. Write a response that appropriately completes the request.

            ### Instruction:
            {summary_generation_prompt}

            ### Input:
            Task title:  {title}

            Step: {step}

            Details: {truncate_details(details)}

            ### Response:
            """
            model_batch_request.formatted_prompts.append(model_input)

        llm_responses = self.llm.batch_call_model(model_batch_request)

        llm_summaries: MultipleSummaryGenerationResponse = MultipleSummaryGenerationResponse()
        for text in llm_responses.text:
            llm_summaries.summary.append(process_response_text(extract_qa_answer(text)))

        return llm_summaries
