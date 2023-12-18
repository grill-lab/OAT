import re

from .abstract_safety_check import AbstractSafetyCheck
from safety_pb2 import SafetyAssessment, SafetyUtterance
from utils import logger


class SensitivityCheck(AbstractSafetyCheck):

    SENSITIVE_REGEXES = [
        # Politics sensitivity
        r'\btrump\b.*\b(china|north korea|syria|russia|world|war|nation|country|wall|politic|policy|immigration'
        r'|religion|global warming|government|right)\b',
        r'\b(china|north korea|syria|russia|world|war|nation|country|wall|politic|policy|immigration|religion|global '
        r'warming|government|gun)\b.*\btrump\b',
        r'\brelig(ion|ious)\b|\bmuslim\b|\bislam\b|\bchristian\b|\bchurch\b',
        r'\btrump\b|\bimmigrant(|s|ion)\b|\bpolitic('
        r'|s)\b|\bpolicy\b|\bgovernment\b|\bexecutive\b|\bjudicial\b|\bcongress\b|\blaw\b|\bpresident\b|\bsenate\b'
        r'|\bdrone\b|\brepublican(|s)\b|\bdemocrat(|s)',
        # Sexual sensitivity
        r'\bsex(|ual|ually)\b|\brap(e|ed|ing)\b|\berotic\b|\bgay\b|\bhomophobic\b|\blesbian\b|\bbisexual\b|\bsexual '
        r'violence\b|chlamydia\b',
        # Racism, ageism, classism, and discrimination
        r'\b(black|white|yellow) (man|woman|people)\b|\blow(|er) class\b|\bold (people|man|woman)\b',
        # Grief and loss, trauma, or violence sensitivity
        r'\bdea(th|d)\b|\bkill(|ed)\b|\bsuicide\b|\beuthanasia\b',
        # Employment sensitivity
        r'\bpoorb|\bunemployed\b|\bfired\b|\bloan\b|\b(start a)business\b|\bcontract\b',
    ]

    def __init__(self):
        logger.debug(f'sensitivity regexes: {self.SENSITIVE_REGEXES}')

    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        Assesses whether an utterance is safe based on sensitivity check.
        """
        logger.debug(f'sensitivity utterance: {utterance.text}')
        safety_assessment = SafetyAssessment()

        # Loop of regexes that identify sensitive utterances.
        for q in self.SENSITIVE_REGEXES:
            if re.search(q, utterance.text.lower()):
                safety_assessment.is_safe = False
                logger.debug(f'-> safety_assessment (sensitivity): {safety_assessment.is_safe} -> due to: {q}')
                return safety_assessment

        # Return safe if no sensitivity regexes identified in utterances.
        safety_assessment.is_safe = True
        logger.info(f'-> safety_assessment (sensitivity): {safety_assessment.is_safe}')
        return safety_assessment
