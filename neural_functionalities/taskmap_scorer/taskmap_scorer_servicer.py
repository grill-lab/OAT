from searcher_pb2 import ScoreCandidateInput, ScoreCandidateOutput
from searcher_pb2_grpc import ScoreCandidateServicer, add_ScoreCandidateServicer_to_server

from . import DefaultScorer


class Servicer(ScoreCandidateServicer):

    def __init__(self):
        self.scorer = DefaultScorer()

    def score_candidate(self, score_candidate_input: ScoreCandidateInput, context) -> ScoreCandidateOutput:
        return self.scorer.score_candidate(score_candidate_input)
