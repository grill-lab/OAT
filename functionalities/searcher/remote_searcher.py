import os

from searcher_pb2 import SearchQuery, SearchResults
from .abstract_searcher import AbstractSearcher
from searcher_pb2_grpc import SearcherStub
import grpc
from utils import logger


class RemoteSearcher(AbstractSearcher):

    def __init__(self, environ_var: str):
        self.endpoint_var = environ_var
        channel = grpc.insecure_channel(os.environ.get(environ_var))
        self.searcher_stub = SearcherStub(channel)

    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        try:
            search_result = self.searcher_stub.search_taskmap(query)
        except grpc.RpcError:
            search_result = SearchResults()
            logger.warning("Endpoint did not respond. Is the Environment variable %s set?" % self.endpoint_var)

        return search_result
