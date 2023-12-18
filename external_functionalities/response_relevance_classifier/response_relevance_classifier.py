from utils import logger

from .abstract_response_relevance_classifier import AbstractResponseClassifier
from qa_response_relevance_pb2 import RelevanceAssessment, AssessmentRequest


class QAResponseClassifier(AbstractResponseClassifier):

    @staticmethod
    def assess_relevance(assessment_request: AssessmentRequest) -> RelevanceAssessment:
        """ TO DO: better mock implementation """
        relevance_assessment = RelevanceAssessment()
        logger.info(assessment_request)

        relevance_assessment.score = float(1)
        relevance_assessment.is_relevant = True if int(relevance_assessment.score) == 1 else False

        return relevance_assessment

    def assess_response_relevance(self, assessment_request: AssessmentRequest) -> RelevanceAssessment:
        return self.assess_relevance(assessment_request)
