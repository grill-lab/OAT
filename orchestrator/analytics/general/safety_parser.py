from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session
import grpc
import os
from utils import logger
from safety_pb2_grpc import SafetyStub
from safety_pb2 import SafetyUtterance


class SafetyParser(AbstractParser):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.safety_service = SafetyStub(channel)

    def check_utterance(self, utterance):
        # return True, True, True, True

        if utterance == "":
            # If empty string, we consider all tests to be positive
            return True, True, True, True

        utterance_request = SafetyUtterance()
        utterance_request.text = utterance

        # Safety checks.
        privacy_assessment = self.safety_service.privacy_check(utterance_request)
        sensitivity_assessment = self.safety_service.sensitivity_check(utterance_request)
        offensive_speech_assessment = self.safety_service.offensive_speech_check(utterance_request)
        suicide_prevention_assessment = self.safety_service.suicide_prevention_check(utterance_request)

        return (
            privacy_assessment.is_safe,
            sensitivity_assessment.is_safe,
            offensive_speech_assessment.is_safe,
            suicide_prevention_assessment.is_safe
        )

    def __call__(self, session: Session) -> Session:
        """ Assess safety of user utterance """

        # Safety checks.
        (
            privacy_safe,
            sensitivity_safe,
            offensive_speech_safe,
            suicide_prevention_safe
        ) = self.check_utterance(session.turn[-1].user_request.interaction.text)

        if not privacy_safe:
            session.turn[-1].user_request.interaction.intents.append('PrivacyViolationIntent')
        if not sensitivity_safe:
            session.turn[-1].user_request.interaction.intents.append('SensitivityViolationIntent')
        if not offensive_speech_safe:
            session.turn[-1].user_request.interaction.intents.append('OffensiveIntent')
        if not suicide_prevention_safe:
            session.turn[-1].user_request.interaction.intents.append('SuicideIntent')

        return session
