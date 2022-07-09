from abc import ABC, abstractmethod
from typing import Union

from phase_intent_classifier_pb2 import (IntentRequest, IntentClassification)

class AbstractClassifier(ABC):

    @abstractmethod
    def classify_intent(
            self, intent_request: IntentRequest
    ) -> IntentClassification:
        """
        Takes in the current utterance and outputs an intent classification from a neural model.
        Classification depends on what phase the user is in the system, hence the multiple
        return types.
        """
        pass

