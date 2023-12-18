from abc import ABC, abstractmethod
from semantic_searcher_pb2 import SemanticQuery, ThemeDocument


class AbstractSemanticSearcher(ABC):

    @abstractmethod
    def search_theme(self, query: SemanticQuery) -> ThemeDocument:
        """
        Semantic search over list of themes. Returns 0 or 1 theme document
        based on threshold
        """
        pass