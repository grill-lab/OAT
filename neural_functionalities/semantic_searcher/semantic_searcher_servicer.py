from semantic_searcher_pb2 import SemanticQuery, ThemeMapping
from semantic_searcher_pb2_grpc import SemanticSearcherServicer, add_SemanticSearcherServicer_to_server
from . import DefaultSemanticSearcher


class Servicer(SemanticSearcherServicer):

    def __init__(self):
        self.searcher = DefaultSemanticSearcher()

    def search_theme(self, query: SemanticQuery, context) -> ThemeMapping:
        return self.searcher.search_theme(query)
