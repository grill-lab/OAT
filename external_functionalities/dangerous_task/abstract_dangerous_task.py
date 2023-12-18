from abc import ABC, abstractmethod
from taskmap_pb2 import TaskMap
from dangerous_task_pb2 import DangerousAssessment


class AbstractDangerousTask(ABC):

    @abstractmethod
    def test_dangerous_task(self, taskmap: TaskMap) -> DangerousAssessment:
        """
        This function assesses whether a task is dangerous for the user or their property.
        """
        pass
