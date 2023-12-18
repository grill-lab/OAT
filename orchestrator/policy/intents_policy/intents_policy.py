from typing import Dict, Tuple

from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import OutputInteraction, Session
from utils import logger

from .abstract_intent_handler import AbstractIntentHandler
from .cancel_handler import CancelHandler
from .help_handler import HelpHandler
from .timer_handler import TimerHandler

handlers_list = [TimerHandler, HelpHandler, CancelHandler]


class IntentsPolicy(AbstractPolicy):

    # This policy does not support yet Phase Changes

    def __init__(self) -> None:
        handlers_instances = [handler_class() for handler_class in handlers_list]

        self.handlers_map: Dict[str, AbstractIntentHandler] = dict()
        for handler in handlers_instances:
            for intent in handler.caught_intents:
                assert intent not in self.handlers_map, \
                    f"Collision between intent handlers {handler.__class__.__name__} and " \
                    f"{self.handlers_map[intent].__class__.__name__}, handling the same intent {intent}"
                self.handlers_map[intent] = handler

    def triggers(self, session: Session) -> bool:
        """Check if the IntentsPolicy should be triggered on the current Session.

        This method is used to check if the ``step`` method should be called. It 
        returns False immediately if there are no intents associated with the current
        InputInteraction from the most recent turn. If there are any intents, it will
        check the first entry in the list against the intents that can be handled by
        its set of handler classes, and return True if there is a match.

        Args:
            session (Session): the current Session object

        Returns:
            bool: True if the policy can handle an intent, False otherwise
        """
        if len(session.turn[-1].user_request.interaction.intents) == 0:
            return False

        intent = session.turn[-1].user_request.interaction.intents[0]
        logger.info(f"Client has sent {intent} intent")

        return intent in self.handlers_map.keys()

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the IntentsPolicy class.

        This method should only be called after calling ``triggers`` and checking
        it returns True, otherwise it'll raise an assertion. 

        Assuming there is a valid intent to handle, it will simply look up the 
        matching Handler class and call its step method, returning the result.

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """
        assert len(session.turn[-1].user_request.interaction.intents) != 0, \
            "No Intents when calling the Intent policy"

        intent = session.turn[-1].user_request.interaction.intents[0]
        return self.handlers_map[intent].step(session=session)
