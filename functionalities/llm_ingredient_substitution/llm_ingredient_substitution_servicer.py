from compiled_protobufs.llm_pb2 import (
    IngredientReplacementRequest, IngredientReplacementResponse,
    AdjustedStepGenerationRequest, AdjustedStepGenerationResponse
)
from compiled_protobufs.llm_pb2_grpc import (
    LLMReplacementGenerationServicer, add_LLMReplacementGenerationServicer_to_server
)

from . import DefaultLLMIngredientSubstitutionGenerator
from . import DefaultLLMIngredientStepTextRewriter


class Servicer(LLMReplacementGenerationServicer):
    def __init__(self):
        self.replacement_generator = DefaultLLMIngredientSubstitutionGenerator()
        self.step_rewriter = DefaultLLMIngredientStepTextRewriter()

    def generate_replacement(self, request: IngredientReplacementRequest, context) -> IngredientReplacementResponse:
        return self.replacement_generator.generate_replacement(request)

    def adjust_step_texts(self, request: AdjustedStepGenerationRequest, context) -> AdjustedStepGenerationResponse:
        return self.step_rewriter.adjust_step_texts(request)
