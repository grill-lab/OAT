from video_searcher_pb2 import TaskStep, ActionClassification
from video_searcher_pb2_grpc import ActionClassifierServicer, add_ActionClassifierServicer_to_server
from .cooking_methods_check import MethodsCheck

from utils import logger


class Servicer:

    def __init__(self):
        logger.info('Initialising action classification model')
        self.classifier: MethodsCheck = MethodsCheck()

    def classify_action_step(self, action_step: TaskStep, context) -> ActionClassification:
        return self.classifier.classify_action_step(action_step)
