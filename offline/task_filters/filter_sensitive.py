import re

from .filter_abstract import AbstractTaskFilter
from safety_pb2 import SafetyAssessment
from taskmap_pb2 import TaskMap

from utils import logger
from typing import List


class SensitiveTaskFilter(AbstractTaskFilter):
    """ Filters TaskGraphs which fail sensitive assessment."""

    def __init__(self):
        super().__init__()
        self.filter_name = "sensitive-filter"
        self.sensitive_classifier = SensitiveClassifier()
    
    def is_task_valid(self, taskmap: TaskMap) -> bool:
        is_valid = self.__is_safe(taskmap)
        if is_valid:
            self.passed_taskmap_count += 1
        else:
            self.failed_taskmap_count += 1
            self.failed_urls.append(taskmap.source_url)
        return is_valid

    def __is_safe(self, taskmap: TaskMap) -> bool:
        title = taskmap.title.lower()
        task_sensitive_assessment = self.sensitive_classifier.test_utterance_safety(title.lower())
        return task_sensitive_assessment.is_safe


class SensitiveClassifier:

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
        r'\bsex(|ual)\b|\brap(e|ed|ing)\b|\berotic\b|\bgay\b|\bhomophobic\b|\blesbian\b|\bbisexual\b|\bsexual '
        r'violence\b',
        # Racism, ageism, classism, and discrimination
        r'\b(black|white|yellow) (man|woman|people)\b|\blow(|er) class\b|\bold (people|man|woman)\b',
        # Grief and loss, trauma, or violence sensitivity
        r'\bdea(th|d)\b|\bkill(|ed)\b|\bsuicide\b|\beuthanasia\b',
        # Employment sensitivity
        r'\bpoorb|\bunemployed\b|\bfired\b',
    ]

    def __init__(self):
        logger.debug(f'sensitivity regexes: {self.SENSITIVE_REGEXES}')

    def test_utterance_safety(self, utterance) -> SafetyAssessment:
        """
        Assesses whether an utterance is safe based on sensitivity check.
        """
        logger.debug(f'sensitivity utterance: {utterance}')
        safety_assessment = SafetyAssessment()

        # Loop of regexes that identify sensitive utterances.
        for q in self.SENSITIVE_REGEXES:
            if re.search(q, utterance):
                safety_assessment.is_safe = False
                logger.debug(f'-> safety_assessment (sensitivity): {safety_assessment.is_safe} -> due to: {q}')
                return safety_assessment

        # Return safe if no sensitivity regexes identified in utterances.
        safety_assessment.is_safe = True
        logger.info(f'-> safety_assessment (sensitivity): {safety_assessment.is_safe}')
        return safety_assessment
 