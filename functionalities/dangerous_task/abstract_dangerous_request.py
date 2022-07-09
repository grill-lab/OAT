from abc import ABC, abstractmethod
from taskmap_pb2 import Session
from dangerous_task_pb2 import DangerousAssessment


class AbstractDangerousRequest(ABC):

    @abstractmethod
    def assess_user_request(self, session: Session) -> DangerousAssessment:
        """
        This function assesses whether a user's request is potentially dangerous.
        """
        pass