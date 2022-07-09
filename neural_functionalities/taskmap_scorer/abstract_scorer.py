
from abc import ABC, abstractmethod
from searcher_pb2 import ScoreTaskMapInput, ScoreTaskMapOutput


class AbstractScorer(ABC):

    @abstractmethod
    def score_taskmap(self, score_taskmap_input: ScoreTaskMapInput) -> ScoreTaskMapOutput:
        """
        This method scores a taskmap based on ScoreTaskMapInput
        """
        pass