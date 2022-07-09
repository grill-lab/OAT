from personality_pb2_grpc import PersonalityServicer, add_PersonalityServicer_to_server
from personality_pb2 import PersonalityResponse, PersonalityRequest

from . import DefaultPersonalityProcessor

class Servicer(PersonalityServicer):

    def __init__(self):
        self.personality_processor = DefaultPersonalityProcessor()

    def process_utterance(self, personality_request: PersonalityRequest, context) -> PersonalityResponse:
        return self.personality_processor.process_utterance(personality_request)

