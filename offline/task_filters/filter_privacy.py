from abc import ABC

from .filter_abstract import AbstractTaskFilter
from safety_pb2 import SafetyAssessment
from taskmap_pb2 import TaskMap
from utils import logger


class PrivacyTaskFilter(AbstractTaskFilter):
    """ Filters TaskGraphs which fail privacy assessment."""

    def __init__(self):
        super().__init__()
        self.filter_name = "privacy-filter"
        self.privacy_classifier = PrivacyClassifier()

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
        task_privacy_assessment = self.privacy_classifier.test_utterance_safety(title.lower())
        return task_privacy_assessment.is_safe


class PrivacyClassifier:
    WORDLIST_PATH = "task_filters/privacy_wordlist.txt"

    def __init__(self):
        with open(self.WORDLIST_PATH, 'r') as f:
            self.word_list = []
            for line in f:
                self.word_list.append(line.strip().lower())

    def test_utterance_safety(self, utterance) -> SafetyAssessment:
        """
        Assesses whether an utterance is safe based on privacy concerns.
        """
        logger.debug(f'privacy utterance: {utterance}')
        safety_assessment = SafetyAssessment()

        # Loop of regexes that identify utterances that contain private information.
        for w in self.word_list:
            if w in utterance:
                safety_assessment.is_safe = False
                logger.debug(f'-> safety_assessment (privacy): {safety_assessment.is_safe} -> due to: {w}')
                return safety_assessment

        # Return safe if no private regexes identified in utterances.
        safety_assessment.is_safe = True
        logger.info(f'-> safety_assessment (privacy): {safety_assessment.is_safe}')
        return safety_assessment
