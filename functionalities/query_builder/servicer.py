from searcher_pb2_grpc import QueryBuilder, add_QueryBuilderServicer_to_server
from searcher_pb2 import SearchQuery, ThemeQuery
from taskmap_pb2 import Session

from . import DefaultQueryBuilder, DefaultThemeBuilder


class Servicer(QueryBuilder):

    def __init__(self):
        self.query_builder = DefaultQueryBuilder()
        self.theme_builder = DefaultThemeBuilder()

    def synthesize_query(self, session: Session, context) -> SearchQuery:
        return self.query_builder.synthesize_query(session)

    def theme_recommendation(self, theme_query: ThemeQuery, context) -> SearchQuery:
        return self.theme_builder.theme_query_recommendation(theme_query)