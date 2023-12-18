from typing import List, Tuple

from taskmap_pb2 import OutputInteraction, Session
from utils import close_session, set_source

from .abstract_intent_handler import AbstractIntentHandler


class CancelHandler(AbstractIntentHandler):

    @property
    def caught_intents(self) -> List[str]:
        """Defines the list of intents handled by this class.

        Returns:
            List[str]: list of intent names
        """
        return ['CancelIntent']

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the CancelHandler class.

        This simply calls the ``close_session`` method from the utils package
        to end the current Session. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """
        output = OutputInteraction()
        session, output = close_session(session, output)
        set_source(output)
        return session, output
