from category_retrieval_pb2 import CategorySearchResult
from offline_pb2 import CategoryDocument
from category_retrieval_pb2_grpc import CategoryScorerServicer, add_CategoryScorerServicer_to_server

from . import DefaultCategoryRelevanceScorer


class Servicer(CategoryScorerServicer):

    def __init__(self):
        self.category_scorer = DefaultCategoryRelevanceScorer()

    def score_categories(self, search_result: CategorySearchResult, context) -> CategoryDocument:
        return self.category_scorer.score_categories(search_result)
