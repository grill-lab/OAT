from abc import ABC, abstractmethod
from taskmap_pb2 import Session, OutputInteraction


class AbstractPolicy(ABC):

    # @abstractmethod
    # def can_handle(self, session: Session) -> bool:
    #     pass

    @abstractmethod
    def step(self, session: Session) -> (Session, OutputInteraction):
        pass
