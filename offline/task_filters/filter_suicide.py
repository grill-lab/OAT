from .filter_abstract import AbstractTaskFilter
from safety_pb2 import SafetyAssessment
from taskmap_pb2 import TaskMap
from utils import logger

from typing import List


class SuicideTaskFilter(AbstractTaskFilter):
    """ Filters TaskGraphs which fail suicide assessment."""

    def __init__(self):
        super().__init__()
        self.filter_name = "suicide-filter"
        self.suicide_classifier = SuicideClassifier()
    
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
        task_suicide_assessment = self.suicide_classifier.test_utterance_safety(title.lower())
        return task_suicide_assessment.is_safe


class SuicideClassifier:

    def __init__(self) -> None:
        with open("task_filters/suicidal_phrases.txt") as suicidal_phrases_list:
            self.suicidal_phrases = []

            for line in suicidal_phrases_list:
                self.suicidal_phrases.append(line.strip().lower())

    def test_utterance_safety(self, user_utterance) -> SafetyAssessment:
        safety_assessment: SafetyAssessment = SafetyAssessment()
        safety_assessment.is_safe = True

        for suicidal_word_or_sentence in self.suicidal_phrases:
            suicidal_word_or_sentence = suicidal_word_or_sentence.lower()
            words = suicidal_word_or_sentence.split()

            if len(words) > 1:
                # dangerous words are multiple, thus we match the whole
                suicidal_sentence = suicidal_word_or_sentence
                if suicidal_sentence in user_utterance:
                    logger.info(f"'{suicidal_sentence}' matched '{user_utterance}' as a suicide sentence")
                    safety_assessment.is_safe = False
                    return safety_assessment
            else:
                suicidal_word = suicidal_word_or_sentence
                tokenized_user_utterance = user_utterance.split()
                if suicidal_word in tokenized_user_utterance:
                    logger.info(f"'{suicidal_word}' matched '{user_utterance}' as a suicide word")
                    safety_assessment.is_safe = False
                    return safety_assessment

        return safety_assessment 
