from task_manager_pb2_grpc import TaskManagerServicer, add_TaskManagerServicer_to_server
from task_manager_pb2 import TMRequest, TMResponse, InfoRequest, InfoResponse, ExtraList, TMInfo
from taskmap_pb2 import Transcript, OutputInteraction

from . import DefaultTaskManager


class Servicer(TaskManagerServicer):

    def __init__(self):
        self.manager = DefaultTaskManager()

    def next(self, request: TMRequest, context) -> TMResponse:
        response = self.manager.next(request)
        return response

    def previous(self, request: TMRequest, context) -> TMResponse:
        response = self.manager.previous(request)
        return response

    def repeat(self, request: TMRequest, context) -> TMResponse:
        response = self.manager.repeat(request)
        return response

    def go_to(self, request: TMRequest, context) -> TMResponse:
        response = self.manager.go_to(request)
        return response

    def get_transcript(self, request, context) -> Transcript:
        response = self.manager.get_transcript(request)
        return response

    def get_requirements(self, request: InfoRequest, context) -> InfoResponse:
        return self.manager.get_requirements(request)

    def get_conditions(self, request: InfoRequest, context) -> InfoResponse:
        return self.manager.get_conditions(request)

    def get_actions(self, request: InfoRequest, context) -> InfoResponse:
        return self.manager.get_actions(request)

    def get_extra(self, request: InfoRequest, context) -> ExtraList:
        return self.manager.get_extra(request)

    def more_details(self, request: TMRequest, context) -> OutputInteraction:
        response = self.manager.more_details(request)
        return response

    def get_step(self, request: TMRequest, context) -> OutputInteraction:
        response = self.manager.get_step(request)
        return response

    def get_num_steps(self, request: TMRequest, context) -> TMInfo:
        return self.manager.get_num_steps(request)
