from abc import ABC, abstractmethod
from chitchat_classifier_pb2 import ChitChatRequest, ChitChatResponse


class AbstractChitChatClassifier(ABC):

    @abstractmethod
    def classify_chitchat(self, request: ChitChatRequest) -> ChitChatResponse:
        pass