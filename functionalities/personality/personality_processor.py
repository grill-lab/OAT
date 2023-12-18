import os
from personality_pb2 import PersonalityResponse, PersonalityRequest
from utils import get_file_system, logger
from difflib import get_close_matches


class PersonalityProcessor():

    def __init__(self):
        logger.info('Initialising personality processor!')
        self.responses = [
            "I can't reveal my name, in the spirit of fair competition.",
            "I live in the cloud, so that makes me cloudian.",
            "I don't have an opinion on that. I can help you with cooking and home improvement instead. Shall we resume?"
        ]

        with open("personality/personality_questions_set.txt") as personality_questions_set:
            self.questions_set = {}
            for line in personality_questions_set:
                question, bucket = line.split(",")
                self.questions_set[question] = int(bucket.strip())

            self.personality_questions = self.questions_set.keys()

    def process_utterance(self, personality_request: PersonalityRequest) -> PersonalityResponse:
        utterance = personality_request.utterance.lower()
        logger.info(f"User utterance for personality: {utterance}")

        response = PersonalityResponse()

        for question in self.personality_questions:

            if question.lower() in utterance:
                logger.info(f"Personality Classifier matched: {question}")
                response.is_personalilty_question = True
                bucket = self.questions_set[question]
                response.answer = self.responses[bucket]

        return response
