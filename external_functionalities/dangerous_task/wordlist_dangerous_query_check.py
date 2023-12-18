from .abstract_dangerous_request import AbstractDangerousRequest
from taskmap_pb2 import Session, Task
from dangerous_task_pb2 import DangerousAssessment
from utils import logger
from .utils.dangerous_classifier import DangerousClassifier


class DangerousRequestCheck(AbstractDangerousRequest):

    def __init__(self):
        self.dangerous_classifier = DangerousClassifier()

    def assess_user_request(self, session: Session) -> DangerousAssessment:

        if len(session.task_selection.elicitation_utterances) > 0 and session.task.phase == Task.TaskPhase.PLANNING:
            text = ""
            for utterance in session.task_selection.elicitation_utterances:
                text += utterance + '. '
        else:
            text = session.turn[-1].user_request.interaction.text

        request_dangerous_assessment = self.dangerous_classifier.pred(text.lower())
        logger.warn("User's query is: {}".format(text))
        logger.info(f'-> dangerous_assessment.is_dangerous: {request_dangerous_assessment.is_dangerous}')
        return request_dangerous_assessment
