from dangerous_task_pb2 import DangerousAssessment
from utils import logger


class DangerousClassifier:

    WORDLIST_PATH = 'dangerous_task/utils/wordlist.txt'

    def __init__(self):
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
                    logger.info(f"'{dangerous_sentence}' matched '{user_utterance}' as a dangerous sentence")
                    dangerous_assessment.is_dangerous = True
                    return dangerous_assessment
            else:
                dangerous_word = dangerous_word_or_sentence
                tokenized_user_utterance = user_utterance.split()
                if dangerous_word in tokenized_user_utterance:
                    logger.info(f"'{dangerous_word}' matched '{user_utterance}' as a dangerous word")
                    dangerous_assessment.is_dangerous = True
                    return dangerous_assessment

        return dangerous_assessment
