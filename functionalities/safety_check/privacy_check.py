
from .abstract_safety_check import AbstractSafetyCheck
from safety_pb2 import SafetyAssessment, SafetyUtterance
from utils import get_file_system, logger
import os
import re

class PrivacyCheck(AbstractSafetyCheck):

    WORDLIST_PATH = 'safety_check/utils/wordlist.txt'

    def __init__(self):
        with open(self.WORDLIST_PATH, 'r') as f:
            self.word_list = []
            for line in f:
                self.word_list.append(line.strip().lower())

    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        Assesses whether an utterance is safe based on privacy concerns.
        """
        logger.debug(f'privacy utterance: {utterance.text}')
        safety_assessment = SafetyAssessment()

        # Loop of regexes that identify utterances that contain private information.
        for w in self.word_list:
            if w in utterance.text:
                safety_assessment.is_safe = False
                logger.debug(f'-> safety_assessment (privacy): {safety_assessment.is_safe} -> due to: {w}')
                return safety_assessment

        # Return safe if no private regexes identified in utterances.
        safety_assessment.is_safe = True
        logger.info(f'-> safety_assessment (privacy): {safety_assessment.is_safe}')
        return safety_assessment
