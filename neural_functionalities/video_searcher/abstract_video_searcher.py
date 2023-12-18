from abc import ABC, abstractmethod
from video_searcher_pb2 import VideoQuery, VideoResults


class AbstractVideoSearcher(ABC):

    @abstractmethod
    def search_video(self, query: VideoQuery) -> VideoResults:
        """
        This method scores a taskmap based on ScoreTaskMapInput
        """
        pass
