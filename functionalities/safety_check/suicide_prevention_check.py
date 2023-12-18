from typing import List
from .abstract_safety_check import AbstractSafetyCheck
from safety_pb2 import SafetyAssessment, SafetyUtterance
from utils import logger


class SuicidePreventionCheck(AbstractSafetyCheck):
    def __init__(self) -> None:

        with open("safety_check/suicidal_phrases.txt") as suicidal_phrases_list:
            self.suicidal_phrases = []

            for line in suicidal_phrases_list:
                self.suicidal_phrases.append(line.strip().lower())

    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        user_utterance = utterance.text.lower()

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
