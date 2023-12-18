from compiled_protobufs.llm_pb2 import SummaryGenerationRequest
from compiled_protobufs.llm_pb2 import SummaryGenerationResponse, MultipleSummaryGenerationRequest, MultipleSummaryGenerationResponse
from compiled_protobufs.llm_pb2_grpc import LLMSummaryGenerationServicer, add_LLMSummaryGenerationServicer_to_server
from . import DefaultLLMSummaryGeneration


class Servicer(LLMSummaryGenerationServicer):

    def __init__(self):
        self.summary_generation_model = DefaultLLMSummaryGeneration()

    def generate_summary(self, query: SummaryGenerationRequest, context) -> SummaryGenerationResponse:
        return self.summary_generation_model.generate_summary(query)

    def generate_summaries(self, query: MultipleSummaryGenerationRequest, context) -> MultipleSummaryGenerationResponse:
        return self.summary_generation_model.generate_summaries(query)
