from video_searcher_pb2 import VideoQuery
from video_searcher_pb2_grpc import VideoSearcherServicer, add_VideoSearcherServicer_to_server
from . import DefaultVideoSearcher

from video_document_pb2 import VideoDocument

from utils import init, logger


class Servicer(VideoSearcherServicer):

    def __init__(self):
        logger.debug('initialising video servicer')
        self.searcher = DefaultVideoSearcher()

    def search_video(self, query: VideoQuery, context) -> VideoDocument:
        logger.debug(f'servicer is calling searcher with query: {query}')
        return self.searcher.search_video(query)