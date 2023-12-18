import os

from category_retrieval_pb2 import CategoryQuery, CategorySearchResult
from offline_pb2 import CategoryDocument
from category_retrieval_pb2_grpc import CategorySearcherServicer, add_CategorySearcherServicer_to_server
from . import DefaultCategorySearcher
from utils import logger, get_file_system


class Servicer(CategorySearcherServicer):

    def __init__(self):
        self.searcher = DefaultCategorySearcher()

    def search_category(self, query: CategoryQuery, context) -> CategoryDocument:
        return self.searcher.search_category(query)
