from taskmap_pb2 import Session, OutputInteraction, ScreenInteraction
from .abstract_intent_handler import AbstractIntentHandler
from utils import close_session

class CancelHandler(AbstractIntentHandler):

    @property
    def caught_intents(self):
        return ['AMAZON.NavigateHomeIntent']

    def step(self, session: Session) -> (Session, OutputInteraction):

        output = OutputInteraction()
        session, output = close_session(session, output)

        return session, output
