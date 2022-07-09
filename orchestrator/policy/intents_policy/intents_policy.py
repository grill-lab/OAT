from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, OutputInteraction
from typing import Dict
from .abstract_intent_handler import AbstractIntentHandler
from utils import logger

from .timer_handler import TimerHandler
from .help_handler import HelpHandler
from .cancel_handler import CancelHandler

handlers_list = [TimerHandler, HelpHandler, CancelHandler]


class IntentsPolicy(AbstractPolicy):

    # This policy does not support yet Phase Changes

    def __init__(self):
        handlers_instances = [handler_class() for handler_class in handlers_list]

        self.handlers_map: Dict[str, AbstractIntentHandler] = dict()
        for handler in handlers_instances:
            for intent in handler.caught_intents:
                assert intent not in self.handlers_map, \
                    f"Collision between intent handlers {handler.__class__.__name__} and " \
                    f"{self.handlers_map[intent].__class__.__name__}, handling the same intent {intent}"
                self.handlers_map[intent] = handler

    def triggers(self, session: Session) -> bool:

        if len(session.turn[-1].user_request.interaction.intents) == 0:
            return False

        intent = session.turn[-1].user_request.interaction.intents[0]
        logger.info(f"Client has sent {intent} intent")

        return intent in self.handlers_map.keys()

    def step(self, session: Session) -> (Session, OutputInteraction):

        assert len(session.turn[-1].user_request.interaction.intents) != 0, \
            "No Intents when calling the Intent policy"

        intent = session.turn[-1].user_request.interaction.intents[0]
        return self.handlers_map[intent].step(session=session)
