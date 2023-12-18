from .abstract_dangerous_task import AbstractDangerousTask
from taskmap_pb2 import TaskMap
from dangerous_task_pb2 import DangerousAssessment
from utils import logger
from .utils.dangerous_classifier import DangerousClassifier


class DangerousTaskCheck(AbstractDangerousTask):
    def __init__(self):
        self.dangerous_classifier = DangerousClassifier()

    def test_dangerous_task(self, taskmap: TaskMap) -> DangerousAssessment:
        """
        This function assesses whether a task is dangerous for the user or their property.
        """
        title = taskmap.title.lower()
        logger.debug(f'dangerous task TaskMap being tested: {title}')

        task_dangerous_assessment = self.dangerous_classifier.pred(title.lower())

        logger.debug(f'-> dangerous_assessment.is_dangerous: {task_dangerous_assessment.is_dangerous}')

        return task_dangerous_assessment
