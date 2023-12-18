from abc import ABC, abstractmethod
from task_manager_pb2 import TMRequest, TMResponse
from taskmap_pb2 import Transcript, OutputInteraction


class AbstractTaskManager(ABC):

    @abstractmethod
    def next(self, request: TMRequest) -> TMResponse:
        pass

    @abstractmethod
    def previous(self, request: TMRequest) -> TMResponse:
        pass

    @abstractmethod
    def repeat(self, request: TMRequest) -> TMResponse:
        pass

    @abstractmethod
    def go_to(self, request: TMRequest) -> TMResponse:
        pass

    @abstractmethod
    def get_transcript(self, request: TMRequest) -> Transcript:
        pass

    @abstractmethod
    def more_details(self, request: TMRequest) -> OutputInteraction:
        pass
