import sys

from .abstract_offensive_speech_classifier import AbstractSafetyCheck
from safety_pb2 import SafetyAssessment, SafetyUtterance
from utils import logger

sys.path.insert(0, '/shared')


class OffensiveSpeechClassifier(AbstractSafetyCheck):
    """
    Mock offensive speech classifier.
    """
    BLACKLIST = ['crap', 'shit', 'hate', 'smell']
    
    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        Assesses whether the utterance is safe based on offensive speech.
        """
        logger.info(f'Testing for offensive speech -> utterance: {utterance.text}')
        safety_assessment = SafetyAssessment()
        safety_assessment.is_safe = True

        for w in self.BLACKLIST:
            if w in utterance.text.lower():
                safety_assessment.is_safe = True
                logger.info(f'-> safety_assessment (offensive speech): {safety_assessment.is_safe} -> due to: {w}')
                return safety_assessment

        logger.info(f'-> safety_assessment (offensive speech): {safety_assessment.is_safe}')
        return safety_assessment
