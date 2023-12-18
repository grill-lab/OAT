from abc import ABC, abstractmethod
from qa_response_relevance_pb2 import RelevanceAssessment, AssessmentRequest


class AbstractResponseClassifier(ABC):

    @abstractmethod
    def assess_response_relevance(self,
                                  assessment_request: AssessmentRequest) -> RelevanceAssessment:
        """
        This method takes in a generated answer to a user's question and determines
        how relevant the answer is to the question.
        """
        pass
