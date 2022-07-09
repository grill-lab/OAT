from abc import ABC, abstractmethod
from image_searcher_pb2 import ImageRequest
from taskmap_pb2 import Image

class AbstractImageSearcher(ABC):

    @abstractmethod
    def search_image(self, image_request: ImageRequest) -> Image:
        """
        Given a query from a step, return a relevant image
        """
        pass
