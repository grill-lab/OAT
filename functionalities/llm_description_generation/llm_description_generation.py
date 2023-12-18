import grpc
import os

from compiled_protobufs.llm_pb2 import (
    ModelRequest, ModelBatchRequest, LLMDescriptionGenerationRequest, DescriptionGenerationResponse,
    LLMMultipleDescriptionGenerationRequest, MultipleDescriptionGenerationResponse, ModelBatchResponse
)
from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub

from grpc._channel import _InactiveRpcError
from utils import logger


def extract_description(generated_desc):
    start_token = "### Response: "
    if start_token in generated_desc:
        generated_desc = generated_desc.split(start_token)[1]
    if ". " in generated_desc:
        generated_desc = ". ".join(generated_desc.split('.')[:-1]) + "."
    return generated_desc.strip()


class LLMDescriptionGeneration:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)

    def generate_description(self, request: LLMDescriptionGenerationRequest) -> DescriptionGenerationResponse:
        model_request: ModelRequest = ModelRequest()
          
        prompt = f"### Instruction:\n" \
                 f"Generate a 2 sentence description. It should be fun entertaining, sell the task and make the user " \
                 f"want to start it. Imagine it being the intro that just sells the task.\n\n" \
                 f"### Input:\nTask Title: {request.task_title},\nDescription:\n\n" \
                 f"### Response: "

        model_request.formatted_prompt = prompt
        model_request.max_tokens = 128

        llm_response = self.llm.call_model(model_request)

        llm_description: DescriptionGenerationResponse = DescriptionGenerationResponse()
        llm_description.description = extract_description(llm_response.text)
        return llm_description
    
    def generate_descriptions(self, request: LLMMultipleDescriptionGenerationRequest) -> MultipleDescriptionGenerationResponse:
        model_batch_request: ModelBatchRequest = ModelBatchRequest()
        model_batch_request.max_tokens = 64
                        
        for title, ingredients, domain in zip(request.task_title, request.ingredients, request.domains):
            if domain == "wikihow":
                domain = ""
            else:
                domain = f"Domain: Cooking\n"
            prompt = f"### Instruction:\n" \
                     f"Generate a 2 sentence description. It should be fun entertaining, sell the task and make the " \
                     f"user wanna start it. Imagine it being the intro that just sells the task.\n\n" \
                     f"### Input:\nTask Title: {title},\n{domain}Description:\n\n" \
                     f"### Response: "

            model_batch_request.formatted_prompts.append(str(prompt))

        try:
            llm_responses: ModelBatchResponse = self.llm.batch_call_model(model_batch_request)
        except _InactiveRpcError as e:
            logger.info('LLM Channel is down during description generation')
            llm_responses = ModelBatchResponse()

        llm_descriptions: MultipleDescriptionGenerationResponse = MultipleDescriptionGenerationResponse()
        for text in llm_responses.text:
            llm_descriptions.description.append(extract_description(text))
            
        return llm_descriptions

