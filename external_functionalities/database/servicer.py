from database_pb2_grpc import DatabaseServicer
from database_pb2_grpc import add_DatabaseServicer_to_server
from database_pb2 import Void
from taskmap_pb2 import Session, TaskMap
from searcher_pb2 import TaskMapList
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

    def get_theme_results(self, request, context) -> TaskMapList:
        return self.instance.get_theme_results(request.theme_word)

    def get_queries(self, request, context):
        return self.instance.get_queries()

    def get_theme(self, request, context):
        return self.instance.get_theme(request)
