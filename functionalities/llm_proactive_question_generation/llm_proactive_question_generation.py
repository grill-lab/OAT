import grpc
import os
import re

from compiled_protobufs.llm_pb2 import (
    ModelRequest, ModelBatchRequest, ModelBatchResponse,
    ProactiveQuestionGenerationResponse, ProactiveQuestionGenerationRequest
)
from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub
from taskmap_pb2 import ExtraInfo

from utils import logger
from grpc._channel import _InactiveRpcError


def extract_question(generated_question):
    start_token = "### Response: "
    end_token = "?"
    if start_token in generated_question:
        generated_question = generated_question.split(start_token)[1]
    if end_token in generated_question:
        generated_question = generated_question.split(end_token)[0]
    generated_question = generated_question.replace('\n', " ")
    if ". " in generated_question:
        generated_question = ". ".join(generated_question.split('.')[:-1])
    return generated_question.strip("- ")


def process_response_text(response_text: str) -> str:
    # remove whitespace
    text = ' '.join(response_text.split("\n"))
    if not re.search(r'[.!?]', text[-1]):
        # If not, add a period (.) to the end of the text
        text += '?'

    # split at punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    complete_sentences = []
    for sentence in sentences:
        if sentence.endswith(('.', '!', '?')):
            # remove numbered lists
            sentence = re.sub(r'\d+\.', '', sentence)
            complete_sentences.append(sentence.strip())
    return ' ' + ' '.join(complete_sentences)


def truncate_details(details: str) -> str:
    details_list = details.split(" ")
    n = min(100, len(details_list))
    return " ".join(details_list[:n])


class LLMProactiveQuestionGeneration:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)

    def generate_proactive_questions(self,
                                     request: ProactiveQuestionGenerationRequest) -> ProactiveQuestionGenerationResponse:
        model_batch_request: ModelBatchRequest = ModelBatchRequest()
        model_batch_request.max_tokens = 32

        for title, prev_step, cur_step in zip(request.task_title, request.previous_steps, request.current_step):
            model_input = f"### Instruction: \n You are an intelligent, entertaining, conversational Task assistant, " \
                          f"that knows the all task instructions and wants the user to master them. Assume the user " \
                          f"did everything correctly.\n " \
                          f"###Input:\nTask: {title}\n" \
                          f"Previous Steps:\n{prev_step}\n\n" \
                          f"Current Step:\n{cur_step}\n\n" \
                          f"Ask the user a proactive, question about his experience with one of the previous steps " \
                          f"or how the results turned out.\n\n" \
                          f"### Response: "
            model_batch_request.formatted_prompts.append(model_input)
        try:
            llm_responses: ModelBatchResponse = self.llm.batch_call_model(model_batch_request)
        except _InactiveRpcError as e:
            logger.info('LLM Channel is down during proactive question generation')
            llm_responses = ModelBatchResponse()

        llm_questions: ProactiveQuestionGenerationResponse = ProactiveQuestionGenerationResponse()
        for text in llm_responses.text:
            extra_info: ExtraInfo = ExtraInfo()
            extra_info.text = process_response_text(extract_question(text))
            extra_info.type = ExtraInfo.InfoType.QUESTION
            llm_questions.questions.append(extra_info)

        return llm_questions
