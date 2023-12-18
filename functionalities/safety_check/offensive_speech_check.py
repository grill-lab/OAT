import grpc
import os

from .abstract_safety_check import AbstractSafetyCheck
from utils import logger
from safety_pb2_grpc import SafetyStub
from safety_pb2 import SafetyAssessment, SafetyUtterance


class OffensiveSpeechCheck(AbstractSafetyCheck):

    def __init__(self):
        logger.info('Initialising Offensive Speech from InternalGrill')

    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        Assesses whether an utterance is safe based on offensive speech.
        """
        logger.debug(f'inside offensive speech check in internal grill : {utterance.text}')

        logger.debug(f"Initialised GRPC connection to {os.environ['EXTERNAL_FUNCTIONALITIES_URL']}")
        channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        safety = SafetyStub(channel)
        safety_assessment = safety.offensive_speech_check(utterance)
        logger.info(f'OAT safety_assessment : {safety_assessment.is_safe}')

        return safety_assessment
