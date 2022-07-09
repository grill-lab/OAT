from .filter_utils.methods_classifier import FindCookingMethodsV0
from video_searcher_pb2 import TaskStep, ActionClassification
from utils import logger


class MethodsCheck:

    def __init__(self):
        self.methods_classifier = FindCookingMethodsV0()

    def classify_action_step(self, action_step: TaskStep) -> ActionClassification:
        step_text = action_step.step_text
        action_classification = ActionClassification()

        found_methods = self.methods_classifier.pred(step_text)
        action_classification.is_action = True if len(found_methods) > 0 else False
        for method in found_methods:
            action_classification.methods.append(method)

        return action_classification
