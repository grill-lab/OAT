from typing import List

from .filter_abstract import AbstractTaskFilter
from taskmap_pb2 import TaskMap
from dangerous_task_pb2 import DangerousAssessment


class DangerousTaskFilter(AbstractTaskFilter):
    """ Filters TaskGraphs which fail dangerous assessment."""

    def __init__(self):
        super().__init__()
        self.passed_taskmap_count = 0
        self.failed_taskmap_count = 0
        self.failed_urls: List[str] = []
        self.filter_name = "dangerous-filter"
        self.dangerous_classifier = DangerousClassifier()

    def is_task_valid(self, taskmap: TaskMap) -> bool:
        is_valid = not self.__is_dangerous(taskmap)
        if is_valid:
            self.passed_taskmap_count += 1
        else:
            self.failed_taskmap_count += 1
            self.failed_urls.append(taskmap.source_url)
        return is_valid

    def __is_dangerous(self, taskmap: TaskMap) -> bool:
        title = taskmap.title.lower()
        task_dangerous_assessment = self.dangerous_classifier.pred(title.lower())
        return task_dangerous_assessment.is_dangerous


class DangerousClassifier:
    WORDLIST_PATH = 'task_filters/dangerous_wordlist.txt'

    def __init__(self):
        self.failed_examples: List[str] = []
        with open(self.WORDLIST_PATH, 'r') as f:
            self.word_list = []
            for line in f:
                self.word_list.append(line.strip().lower())

    def pred(self, user_utterance: str) -> DangerousAssessment:

        dangerous_assessment = DangerousAssessment()
        dangerous_assessment.is_dangerous = False
        user_utterance = user_utterance.lower()

        for dangerous_word_or_sentence in self.word_list:
            dangerous_word_or_sentence = dangerous_word_or_sentence.lower()
            words = dangerous_word_or_sentence.split()

            if len(words) > 1:
                # dangerous words are multiple, thus we match the whole
                dangerous_sentence = dangerous_word_or_sentence
                if dangerous_sentence in user_utterance:
                    self.failed_examples.append(
                        f"'{dangerous_sentence}' matched '{user_utterance}' as a dangerous sentence")
                    dangerous_assessment.is_dangerous = True
                    return dangerous_assessment
            else:
                dangerous_word = dangerous_word_or_sentence
                tokenized_user_utterance = user_utterance.split()
                if dangerous_word in tokenized_user_utterance:
                    self.failed_examples.append(f"'{dangerous_word}' matched '{user_utterance}' as a dangerous word")
                    dangerous_assessment.is_dangerous = True
                    return dangerous_assessment

        return dangerous_assessment
