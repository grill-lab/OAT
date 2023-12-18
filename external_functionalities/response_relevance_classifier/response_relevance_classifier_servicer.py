from qa_response_relevance_pb2 import RelevanceAssessment, AssessmentRequest
from qa_response_relevance_pb2_grpc import ResponseRelevanceServicer, add_ResponseRelevanceServicer_to_server

from . import DefaultResponseClassifier


class Servicer(ResponseRelevanceServicer):
    def __init__(self):
        self.response_relevance_classifier = DefaultResponseClassifier()

    def assess_response_relevance(self,
                                  assessment_request: AssessmentRequest, context) -> RelevanceAssessment:
        return self.response_relevance_classifier.assess_response_relevance(assessment_request)
