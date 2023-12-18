import grpc
import os
import re
import time

from compiled_protobufs.chitchat_classifier_pb2 import ChitChatResponse
from compiled_protobufs.llm_pb2 import ModelRequest, ModelResponse, LLMChitChatRequest
from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub

from grpc._channel import _InactiveRpcError
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from utils import logger


def extract_qa_answer(generated_answer):
    start_token = "Your response:"
    end_token_1 = "Human"
    end_token_2 = "#"
    if start_token in generated_answer:
        generated_answer = generated_answer.split(start_token)[-1]
    if end_token_2 in generated_answer:
        generated_answer = generated_answer.split(end_token_2)[0]
    if end_token_1 in generated_answer:
        generated_answer = generated_answer.split(end_token_1)[0]
    generated_answer = generated_answer.replace('\n', " ").replace('You: ', '')
    return generated_answer.strip()


def process_response_text(response_text: str) -> str:
    # remove whitespace
    text = ' '.join(response_text.split("\n"))

    # split at punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    complete_sentences = []
    for sentence in sentences:
        if sentence.endswith(('.', '!', '?')):
            complete_sentences.append(sentence.strip())

    output = ' '.join(complete_sentences)
    if "#" in output:
        logger.warning(f'EXTRACTED LLM RESPONSE BAD!!: {output}')
        return ""
    return output


class LLMChitChat:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)

    @staticmethod
    def build_prompt(request: LLMChitChatRequest) -> ModelRequest:
        model_request: ModelRequest = ModelRequest()

        prompt = "### Instruction: \n"

        if request.task_title != "":
            prompt += f'You are a friendly AI assistant who is assisting a human making {request.task_title}. '
        else:
            prompt += f'You are a friendly AI assistant who is assisting a human. '
        prompt += 'Respond to the human or ask a question back. Try to not repeat what you said previously. '
        prompt += f'You specialize in cooking, arts & crafts, and DIY. You do not reveal your name in the spirit of ' \
                  f'fair competition. You cannot play music, games or quizzes. You are not able to read the news, ' \
                  f'turn on a light, or give recommendations for things outside cooking and DIY domains \n\n'

        if request.last_intent == "ChitChatIntent":
            prompt += f"### Input: \n"
            prompt += f'Human: {request.user_question} \n'
        else:
            if request.last_intent == "QuestionIntent":
                prompt += f"You just said: {request.last_agent_response}. Answer the given user question. \n"
                prompt += f"### Input: \n"
                prompt += f'Human: {request.user_question} \n'
            else:
                prompt += f"### Input: \n"
                prompt += f'You: {request.last_agent_response} \n' \
                          f'Human: {request.user_question} \n'
        prompt += f'\n### Response: Your response:'

        model_request.formatted_prompt = prompt
        model_request.max_tokens = 30
        return model_request

    def call_chit_chat_model(self, request: LLMChitChatRequest) -> ChitChatResponse:
        model_request = self.build_prompt(request)

        llm_response: ModelResponse = self.llm.call_model(model_request)
        logger.info(llm_response.text)

        agent_response: ChitChatResponse = ChitChatResponse()
        agent_response.text = process_response_text(extract_qa_answer(llm_response.text))
        if agent_response.text != "":
            logger.info(f'EXTRACTED LLM RESPONSE: {agent_response.text}')

        return agent_response

    def generate_chit_chat(self, request: LLMChitChatRequest, default_timeout=2000) -> ChitChatResponse:
        # CALL CHIT CHAT LLM SERVICE FROM HERE
        # default timeout is 10000, aka 1000 milliseconds aka 1 second

        default_timeout = default_timeout if request.timeout == 0 else request.timeout
        logger.info(default_timeout)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.call_chit_chat_model, request)
            timeout: float = default_timeout / 1000 + time.monotonic()
            try:
                if future.done() or timeout - time.monotonic() > 0:
                    response = future.result(timeout=timeout - time.monotonic())
                    return response

                else:
                    future.cancel()
                    logger.warning(f"Timeout for LLM Chit Chat")
                    response = ChitChatResponse()
                    response.text = ""
                    return response

            except TimeoutError as e:
                future.cancel()
                logger.warning("TimeoutError while running LLM Chit Chat", exc_info=e)
                response = ChitChatResponse()
                response.text = ""
                return response

            except _InactiveRpcError as e:
                future.cancel()
                logger.warning("LLM Channel is down")
                response = ChitChatResponse()
                response.text = ""
                return response

            except Exception as e:
                future.cancel()
                logger.info(type(e))
