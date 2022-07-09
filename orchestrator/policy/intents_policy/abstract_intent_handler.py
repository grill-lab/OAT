from abc import ABC, abstractmethod
from taskmap_pb2 import Session, OutputInteraction
from typing import List


class AbstractIntentHandler(ABC):

    @property
    @abstractmethod
    def caught_intents(self) -> List[str]:
        pass

    @abstractmethod
    def step(self, session: Session) -> (Session, OutputInteraction):
        pass
