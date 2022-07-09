from image_searcher_pb2 import ImageRequest
from taskmap_pb2 import Image
from image_searcher_pb2_grpc import (
    ImageSearcherServicer,
    add_ImageSearcherServicer_to_server,
)
from . import DefaultImageSearcher

class Servicer(ImageSearcherServicer):

    def __init__(self) -> None:
        self.image_searcher = DefaultImageSearcher()
    
    def search_image(self, image_request: ImageRequest, context) -> Image:
        return self.image_searcher.search_image(image_request)