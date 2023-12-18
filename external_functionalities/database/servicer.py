from database_pb2_grpc import DatabaseServicer, add_DatabaseServicer_to_server
from database_pb2 import Void, QueryList
from taskmap_pb2 import Session, TaskMap
from theme_pb2 import ThemeResults
from . import DefaultDB


class Servicer (DatabaseServicer):

    def __init__(self):
        self.instance = DefaultDB()

    def load_session(self, request, context) -> Session:
        return self.instance.load_session(request.id)

    def save_session(self, request, context) -> None:
        self.instance.save_session(request.id, request.session)
        return Void()

    def load_taskmap(self, request, context) -> TaskMap:
        return self.instance.get_taskmap(request.id)

    def save_taskmap(self, request, context) -> None:
        self.instance.save_session(request.id, request.taskmap)
        return Void()

    def save_search_logs(self, request, context) -> None:
        self.instance.save_search_log(request)
        return Void()

    def save_asr_logs(self, request, context) -> None:
        self.instance.save_asr_log(request)
        return Void()

    def get_theme_by_id(self, request, context) -> ThemeResults:
        return self.instance.get_theme_by_id(request)

    def get_queries(self, request, context):
        return self.instance.get_queries()

    def get_theme(self, request, context):
        return self.instance.get_theme(request)

    def get_theme_by_date(self, request, context) -> QueryList:
        return self.instance.get_theme_by_date(request)
