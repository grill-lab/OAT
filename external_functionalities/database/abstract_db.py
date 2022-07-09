from abc import ABC, abstractmethod
from taskmap_pb2 import Session, TaskMap


class AbstractDB(ABC):

    @abstractmethod
    def load_session(self, session_id: str) -> Session:
        pass

    @abstractmethod
    def save_session(self, session_id: str, session: Session) -> None:
        pass

    @abstractmethod
    def load_taskmap(self, taskmap_id: str) -> TaskMap:
        pass

    @abstractmethod
    def save_taskmap(self, session_id: str, session: Session) -> None:
        pass
