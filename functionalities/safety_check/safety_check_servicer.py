from safety_pb2_grpc import SafetyServicer, add_SafetyServicer_to_server
from safety_pb2 import SafetyUtterance

from . import DefaultPrivacyCheck, DefaultSensitivityCheck, DefaultOffensiveSpeechCheck, DefaultSuicidePreventionCheck


class Servicer(SafetyServicer):


    def __init__(self):
        self.privacy = DefaultPrivacyCheck()
        self.sensitivity = DefaultSensitivityCheck()
        self.offensive_speech = DefaultOffensiveSpeechCheck()
        self.suicide_prevention = DefaultSuicidePreventionCheck()

    def privacy_check(self, utterance: SafetyUtterance, context):
        return self.privacy.test_utterance_safety(utterance)

    def sensitivity_check(self, utterance: SafetyUtterance, context):
        return self.sensitivity.test_utterance_safety(utterance)

    def offensive_speech_check(self, utterance: SafetyUtterance, context):
        return self.offensive_speech.test_utterance_safety(utterance)
    
    def suicide_prevention_check(self, utterance: SafetyUtterance, context):
        return self.suicide_prevention.test_utterance_safety(utterance)
