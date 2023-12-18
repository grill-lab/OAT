import grpc
import os
import json
import time

from compiled_protobufs.llm_pb2 import ExecutionSearchResponse, ExecutionSearchRequest, ModelResponse, ModelRequest
from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub
from compiled_protobufs.taskmap_pb2 import Session

from grpc._channel import _InactiveRpcError
from concurrent.futures import TimeoutError, ThreadPoolExecutor

from utils import logger, SEARCH_AGAIN_QUESTION


class ExecutionSearchManager:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)
        self.valid_intents = [
            'recommend_new_search', 'continue_current_task', 'ask_clarifying_question'
        ]

    def extract_classification_response(self, generated_answer) -> dict:
        logger.info(f'Raw LLM response for classification: {generated_answer}')
        valid_dict = {}
        start_token = "{"
        end_token = "}"
        if end_token not in generated_answer:
            return valid_dict

        if start_token in generated_answer:
            generated_answer = "{" + generated_answer.split(start_token)[-1]

        try:
            generated_answer = generated_answer.replace(' \n   ', '').replace('\n', '')
            valid_dict = json.loads(generated_answer)
            logger.info(f'Managed to parse classification: {valid_dict}')

            if "intent" in list(valid_dict.keys()) and valid_dict["intent"] in self.valid_intents:
                return valid_dict
            else:
                logger.info(f'Dictionary contents not valid: {valid_dict}')
        except Exception as e:
            logger.info(f'Could not parse response >{generated_answer}<: {e}')
            return valid_dict

    def build_prompt(self, request: ExecutionSearchRequest) -> ModelRequest:
        model_request: ModelRequest = ModelRequest()

        task_type = f"making {request.taskmap.title}" if request.domain == Session.Domain.COOKING \
            else f"with {request.taskmap.title}"
        # instruction
        prompt = f"### Instruction: Imagine you are an AI assistant currently helping a user with {request.taskmap.title}. " \
                 f"You are able to switch to a new task, so based on the last user request you need to decide " \
                 f"whether to continue with {request.taskmap.title}, recommend that you can start new search based " \
                 f"on the last user request, or asking a clarifying question. " \
                 f"Choose one of the intent options and follow this format for your response: {{\"intent\": \"\"}}\n"
        # input
        prompt += f"### Input:\nCurrent task: {request.taskmap.title}\nConversation history:\n"
        if any([request.last_agent_response == prompt for prompt in
                SEARCH_AGAIN_QUESTION]) and "step" in request.last_last_agent_response.lower():
            prompt += f"You: {request.last_last_agent_response}\n"
        else:
            prompt += f"You: {request.last_agent_response}\n"
        prompt += f"Last user request: {request.user_question}\n"
        prompt += f"Intent options:{str(self.valid_intents)}\n\n"
        # response
        prompt += "### Response: Your response:{\"intent\":"

        model_request.formatted_prompt = prompt
        model_request.max_tokens = 20
        return model_request

    def llm_generate_search_decision(self, request: ExecutionSearchRequest) -> ExecutionSearchResponse:
        model_request = self.build_prompt(request)

        llm_response: ModelResponse = self.llm.call_model(model_request)

        llm_classification: ExecutionSearchRequest = ExecutionSearchResponse()
        parsed_result = self.extract_classification_response(llm_response.text)
        if parsed_result == {}:
            return llm_classification

        llm_classification.intent_classification = parsed_result.get("intent", "")
        llm_classification.ai_response = parsed_result.get("ai_response", "")
        return llm_classification

    def generate_decision(self, request: ExecutionSearchRequest, default_timeout=1000) -> ExecutionSearchResponse:
        default_timeout = default_timeout if request.timeout == 0 else request.timeout

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.llm_generate_search_decision, request)
            timeout: float = default_timeout / 1000 + time.monotonic()
            try:
                if future.done() or timeout - time.monotonic() > 0:
                    response = future.result(timeout=timeout - time.monotonic())
                    return response

                else:
                    future.cancel()
                    logger.warning(f"Timeout for Execution Search Decision Generation")
                    response = ExecutionSearchResponse()
                    return response

            except TimeoutError as e:
                future.cancel()
                logger.warning("TimeoutError while running Execution Search Decision Generation", exc_info=e)
                response = ExecutionSearchResponse()
                return response

            except _InactiveRpcError as e:
                future.cancel()
                logger.warning("Execution Search Decision Generation Channel is down")
                response = ExecutionSearchResponse()
                return response
