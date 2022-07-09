from policy.abstract_policy import AbstractPolicy
# from policy.qa_policy import DefaultPolicy as DefaultQAPolicy

from taskmap_pb2 import Session, OutputInteraction, ScreenInteraction, Image, Task, SessionState
from exceptions import PhaseChangeException
from utils import logger, is_in_user_interaction

# from intent_classifier_pb2_grpc import IntentClassifierStub
# from intent_classifier_pb2 import IntentProbList, QuestionIntentCheck

# from neural_intent_classifier_pb2_grpc import NeuralIntentClassifierStub
# from neural_intent_classifier_pb2 import UserUtterance, QuestionClassification

import os
import grpc


class ResumingPolicy(AbstractPolicy):

    @staticmethod
    def __reset_session(session):
        session_id = session.session_id
        new_session = Session()
        new_session.session_id = session_id

        for turn in session.turn:
            new_turn = new_session.turn.add()
            new_turn.ParseFromString(turn.SerializeToString())

        new_session.greetings = session.greetings
        session.ParseFromString(new_session.SerializeToString())

    def step(self, session: Session) -> (Session, OutputInteraction):

        if not session.resume_task:
            self.__reset_session(session)
            logger.info('USER HAS USED BOT BEFORE, BUT RESUME_TASK IS FALSE')

        if session.task.phase in [Task.TaskPhase.DOMAIN,
                                  Task.TaskPhase.PLANNING,
                                  Task.TaskPhase.CLOSING,
                                  Task.TaskPhase.VALIDATING]:
            self.__reset_session(session)

        session.state = SessionState.RUNNING
        # session.task.state.requirements_displayed = False
        # Forces the action on resuming to be the repetition of the last instruction
        session.turn[-1].user_request.interaction.intents.append("RepeatIntent")
        raise PhaseChangeException()
