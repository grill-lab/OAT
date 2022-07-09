from safety_pb2_grpc import SafetyServicer, add_SafetyServicer_to_server
from safety_pb2 import SafetyUtterance

from . import DefaultOffensiveSpeechClassifier


class Servicer(SafetyServicer):


    def __init__(self):
        self.offensive_speech = DefaultOffensiveSpeechClassifier()

    def offensive_speech_check(self, utterance: SafetyUtterance, context):
        return self.offensive_speech.test_utterance_safety(utterance)
