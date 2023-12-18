
from compiled_protobufs.llm_pb2 import ProactiveQuestionGenerationRequest, ProactiveQuestionGenerationResponse
from compiled_protobufs.llm_pb2_grpc import LLMProactiveQuestionGenerationServicer, add_LLMProactiveQuestionGenerationServicer_to_server
from . import DefaultLLMProactiveQuestionGeneration


class Servicer(LLMProactiveQuestionGenerationServicer):

    def __init__(self):
        self.proactive_question_generation_model = DefaultLLMProactiveQuestionGeneration()

    def generate_proactive_question(self, query: ProactiveQuestionGenerationRequest, context) -> ProactiveQuestionGenerationResponse:
        return self.proactive_question_generation_model.generate_proactive_questions(query)
