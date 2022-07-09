from searcher_pb2 import SearchQuery, SearchResults
from searcher_pb2_grpc import SearcherServicer, add_SearcherServicer_to_server

from . import AbstractSearcher
from utils import init
from searcher.config import searcher_config


class Servicer(SearcherServicer):

    def __init__(self):
        self.searcher: AbstractSearcher = init(searcher_config)

    def search_taskmap(self, query: SearchQuery, context) -> SearchResults:
        return self.searcher.search_taskmap(query)
