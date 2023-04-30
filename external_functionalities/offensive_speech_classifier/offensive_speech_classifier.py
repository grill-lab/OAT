import os
from .abstract_offensive_speech_classifier import AbstractSafetyCheck
from safety_pb2 import SafetyAssessment, SafetyUtterance


import sys
sys.path.insert(0, '/shared')
from utils import logger



class OffensiveSpeechClassifier(AbstractSafetyCheck):
    """
    Mock offensive speech classifier.
    """
    BLACKLIST = ['crap', 'shit', 'hate', 'smell']

    def __init__(self):
        logger.info("Initialising Offensive Speech in Alexa Grill")
    
    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        Assesses whether the utterance is safe based on offensive speech.
        """
        safety_assessment = SafetyAssessment()
        safety_assessment.is_safe = True

        for w in self.BLACKLIST:
            tokenized = utterance.text.split()
            if w in tokenized:
                safety_assessment.is_safe = False
                logger.info(f'-> safety_assessment (offensive speech): {safety_assessment.is_safe} -> due to: {w}')
                return safety_assessment

        logger.info(f'{utterance.text} -> safety_assessment (offensive speech): {safety_assessment.is_safe}')
        return safety_assessment
