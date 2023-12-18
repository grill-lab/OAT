from abc import ABC, abstractmethod
from searcher_pb2 import ScoreCandidateInput, ScoreCandidateOutput


class AbstractScorer(ABC):

    @abstractmethod
    def score_candidate(self, score_candidate_input: ScoreCandidateInput) -> ScoreCandidateOutput:
        """
        This method scores a taskmap based on ScoreTaskMapInput
        """
        pass
