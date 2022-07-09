
from searcher_pb2 import ScoreTaskMapInput, ScoreTaskMapOutput
from searcher_pb2_grpc import ScoreTaskMapServicer, add_ScoreTaskMapServicer_to_server

from . import DefaultScorer


class Servicer(ScoreTaskMapServicer):

    def __init__(self):
        self.scorer = DefaultScorer()

    def score_taskmap(self, score_taskmap_input: ScoreTaskMapInput, context) -> ScoreTaskMapOutput:
        return self.scorer.score_taskmap(score_taskmap_input)
