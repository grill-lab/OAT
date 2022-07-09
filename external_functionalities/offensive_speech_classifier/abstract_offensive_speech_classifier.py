from abc import ABC, abstractmethod
from safety_pb2 import SafetyAssessment, SafetyUtterance


class AbstractSafetyCheck(ABC):


    @abstractmethod
    def test_utterance_safety(self, utterance: SafetyUtterance) -> SafetyAssessment:
        """
        This method takes in utterance and assesses whether latest utterance is safe based on specific safety criteria.

        :param Session: {turn:[...], task:{...}...}
        :return: SafetyAssessment: {is_safe: bool}
        """
        pass