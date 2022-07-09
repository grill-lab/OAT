
from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, OutputInteraction

from qa_pb2_grpc import QuestionAnsweringStub, TaskQuestionAnsweringStub
from qa_pb2 import QAQuery, QAResponse, QARequest

from typing import Tuple
import grpc

from utils import logger, close_session, is_in_user_interaction
import os
import random

from intent_classifier_pb2_grpc import IntentClassifierStub
from intent_classifier_pb2 import DomainClassification

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import QuestionClassificationRequest, QuestionClassificationResponse

from dangerous_task_pb2_grpc import DangerousStub


class QAPolicy(AbstractPolicy):

    def __init__(self) -> None:

        functionalities_channel = grpc.insecure_channel(
            os.environ['FUNCTIONALITIES_URL']
        )

        neural_functionalities_channel = grpc.insecure_channel(
            os.environ['NEURAL_FUNCTIONALITIES_URL']
        )

        self.qa_systems = {
            "GENERAL_QA": QuestionAnsweringStub(neural_functionalities_channel),
            "TASKMAP_QA": TaskQuestionAnsweringStub(neural_functionalities_channel),
        }

        self.intent_classifier = IntentClassifierStub(functionalities_channel)
        self.dangerous_task_filter = DangerousStub(functionalities_channel)
        self.qa_system = None

        self.phase_intent_classifier = PhaseIntentClassifierStub(
            neural_functionalities_channel)

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:

        output: OutputInteraction = OutputInteraction()
        output.speech_text = "Great question! I don't know the answer but I don't want that to slow us down. \
                I'm really keen to keep going!"

        return session, output
