from compiled_protobufs.llm_pb2 import LLMDescriptionGenerationRequest, DescriptionGenerationResponse, \
    LLMMultipleDescriptionGenerationRequest, MultipleDescriptionGenerationResponse
from compiled_protobufs.llm_pb2_grpc import LLMDescriptionGenerationServicer, \
    add_LLMDescriptionGenerationServicer_to_server
from . import DefaultLLMDescriptionGeneration


class Servicer(LLMDescriptionGenerationServicer):

    def __init__(self):
        self.description_generation_model = DefaultLLMDescriptionGeneration()

    def generate_description(self, query: LLMDescriptionGenerationRequest, context) -> DescriptionGenerationResponse:
        return self.description_generation_model.generate_description(query)
    
    def generate_descriptions(self, query: LLMMultipleDescriptionGenerationRequest, context) -> \
            MultipleDescriptionGenerationResponse:
        return self.description_generation_model.generate_descriptions(query)
