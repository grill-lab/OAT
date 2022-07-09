from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session


class QuestionIdentificationParser(AbstractParser):

    def __init__(self) -> None:
        """
        Non-exhaustive list of question words
        """
        self.question_words = [
            "how", "what", "when", "where", "which", "did", "does", "need", "do",
            "can", "could", "would", "will", "might", "why", "should", "who", "shall", "may",
            "whom", "shouldn't", "doesn't", "won't", "wouldn't", "doesn't", "don't", "wasn't",
            "weren't", "haven't", "didn't", "whom"
        ]
    
    def __call__(self, session: Session) -> Session:
        
        user_utterance = session.turn[-1].user_request.interaction.text
        is_question = any([user_utterance.lower().startswith(word) for word in self.question_words])

        if is_question:
            session.turn[-1].user_request.interaction.intents.append("QAIntent")

        return session