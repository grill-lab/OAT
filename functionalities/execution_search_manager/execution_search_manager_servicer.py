from compiled_protobufs.llm_pb2 import ExecutionSearchRequest, ExecutionSearchResponse
from compiled_protobufs.llm_pb2_grpc import LLMExecutionSearchManagerServicer, add_LLMExecutionSearchManagerServicer_to_server
from . import DefaultExecutionSearchManager


class Servicer(LLMExecutionSearchManagerServicer):

    def __init__(self):
        self.intent_classification_model = DefaultExecutionSearchManager()

    def generate_decision(self, request: ExecutionSearchRequest, context) -> ExecutionSearchResponse:
        return self.intent_classification_model.generate_decision(request)
