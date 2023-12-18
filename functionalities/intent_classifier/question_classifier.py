from utils import get_file_system, logger

from taskmap_pb2 import Session, InputInteraction
from intent_classifier_pb2 import QuestionIntentCheck


class QuestionIntentClassifier:

    def __init__(self) -> None:
        self.question_words = ['how', 'what', 'when', 'where', 'which', 'did', 'does', 'need',
                               'can', 'could', 'would', 'will', 'might', 'why', 'should', 'who', 'shall', 'may',
                               'whom', "shouldn't", "doesn't", "won't", "wouldn't", "doesn't", "don't", "wasn't",
                               "weren't", "haven't", "didn't", "whom"]

    def classify_intent(self, session: Session) -> QuestionIntentCheck:
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction
        user_utterance = user_interaction.text

        is_question: bool = any([word in user_utterance.lower() for word in self.question_words])

        question_intent_check = QuestionIntentCheck()
        question_intent_check.is_question = is_question

        return question_intent_check
