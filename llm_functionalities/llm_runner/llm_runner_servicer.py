from compiled_protobufs.llm_pb2 import ModelRequest, ModelResponse, ModelBatchRequest, ModelBatchResponse
from compiled_protobufs.llm_pb2_grpc import LLMRunnerServicer, add_LLMRunnerServicer_to_server
from . import DefaultLLMRunner


class Servicer(LLMRunnerServicer):

    def __init__(self):
        self.model = DefaultLLMRunner()

    def call_model(self, query: ModelRequest, context) -> ModelResponse:
        return self.model.call_model(query)
    
    def batch_call_model(self, query: ModelBatchRequest, context) -> ModelBatchResponse:
        return self.model.batch_call_model(query)
