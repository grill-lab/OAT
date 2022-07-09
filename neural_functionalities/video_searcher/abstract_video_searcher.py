from abc import ABC, abstractmethod
from video_searcher_pb2 import VideoQuery, VideoResults
from taskmap_pb2 import Session
from video_document_pb2 import VideoDocument

class AbstractVideoSearcher(ABC):

    @abstractmethod
    def search_video(self, query: VideoQuery) -> VideoResults:
        """
        This method scores a taskmap based on ScoreTaskMapInput
        """
        pass