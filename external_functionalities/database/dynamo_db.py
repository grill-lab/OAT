import os

from searcher_pb2 import SearchLog
from asr_parser_pb2 import ASRLog
from taskmap_pb2 import TaskMap, Session, ConversationTurn
from .abstract_db import AbstractDB
from utils import ProtoDB, ComposedDB
from utils import logger
from theme_pb2 import ThemeResults
from semantic_searcher_pb2 import ThemeMapping
from database_pb2 import QueryList


class DynamoDB(AbstractDB):

    def __init__(self):

        prefix = os.environ.get('DB_ENV', 'Undefined')
        database_url = os.environ.get('DATABASE_URL', None)
        self.session_db = ComposedDB(proto_class=Session,
                                     url=database_url,
                                     prefix=prefix,
                                     primary_key='session_id',
                                     sub_proto_config={
                                         'turn': {
                                             'proto_class': ConversationTurn,
                                             'primary_key': 'id'
                                         }
                                     }
                                     )
        self.taskmap_db = {}  # ProtoDB(proto_class=TaskMap, prefix=prefix, url=database_url)
        self.search_logs_db = ProtoDB(proto_class=SearchLog, prefix=prefix, url=database_url)
        self.asr_logs_db = ProtoDB(proto_class=ASRLog, prefix=prefix, url=database_url)
        self.theme_db = ProtoDB(proto_class=ThemeResults,
                                prefix=prefix,
                                primary_key="theme_word",
                                url=database_url)

        self.mapping_db = ProtoDB(ThemeMapping,
                                  primary_key="theme_query",
                                  prefix="Curated",
                                  url=database_url)

        logger.info("Connection with DynamoDB Tables has been established...")

    def save_session(self, session_id: str, session: Session) -> None:
        self.session_db.put(session)

    def load_session(self, session_id: str) -> Session:
        return self.session_db.get(session_id)

    def save_taskmap(self, session_id: str, session: Session) -> None:
        self.taskmap_db.put(session)

    def load_taskmap(self, taskmap_id: str) -> TaskMap:
        return self.taskmap_db.get(taskmap_id)

    def save_search_log(self, search_log: SearchLog) -> None:
        self.search_logs_db.put(search_log)

    def save_asr_log(self, asr_log: ASRLog) -> None:
        self.asr_logs_db.put(asr_log)

    def get_theme_results(self, theme_word: str) -> ThemeResults:
        return self.theme_db.get(theme_word)

    def get_theme(self, request: ThemeMapping) -> ThemeMapping:
        return self.mapping_db.get(request.theme_query)

    def get_queries(self) -> QueryList:
        response = QueryList()
        response.queries.extend(self.mapping_db.scan_ids())
        return response
