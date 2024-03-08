from compiled_protobufs.llm_pb2 import (
    ModelRequest,
    ModelResponse,
    ModelBatchRequest,
    ModelBatchResponse,
    TGISummaryRequest,
    TGISummaryResponse,
    TGIMultipleSummaryRequest,
    TGIMultipleSummaryResponse,
)
from compiled_protobufs.llm_pb2_grpc import (
    LLMRunnerServicer,
)
from . import DefaultLLMRunner


class Servicer(LLMRunnerServicer):
    def __init__(self):
        self.model = DefaultLLMRunner()

    def call_model(self, query: ModelRequest, context) -> ModelResponse:
        return self.model.call_model(query)

    def batch_call_model(self, query: ModelBatchRequest, context) -> ModelBatchResponse:
        return self.model.batch_call_model(query)

    def generate_summary(self, query: TGISummaryRequest, context) -> TGISummaryResponse:
        return self.model.generate_summary(query)

    def generate_summaries(
        self, query: TGIMultipleSummaryRequest, context
    ) -> TGIMultipleSummaryResponse:
        return self.model.generate_summaries(query)
