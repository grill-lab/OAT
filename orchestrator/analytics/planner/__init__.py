from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session

from .intent_parser import IntentParser
from .vague_parser import VagueParser
from .dangerous_query_parser import DangerousQueryParser
from .question_identification_parser import QuestionIdentificationParser

from utils import is_in_user_interaction


class PlannerParser(AbstractParser):

    def __init__(self):

        self.intent_parser = IntentParser()
        self.vague_parser = VagueParser()
        self.dangerous_query_parser = DangerousQueryParser()
        self.question_identification_parser = QuestionIdentificationParser()

    def __call__(self, session: Session) -> Session:
        # temporary side step
        # first check if there's a question intent before parsing intents
        session = self.question_identification_parser(session)
        if not is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["QAIntent"]
        ):
            session = self.intent_parser(session)
        
        session = self.dangerous_query_parser(session)
        
        if is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["SearchIntent"]
        ):
            session = self.vague_parser(session)

        return session
