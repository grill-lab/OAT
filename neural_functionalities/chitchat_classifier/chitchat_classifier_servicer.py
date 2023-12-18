from chitchat_classifier_pb2_grpc import ChitChatClassifierServicer, add_ChitChatClassifierServicer_to_server
from chitchat_classifier_pb2 import *

from . import DefaultChitChatClassifier
from utils import logger


class Servicer(ChitChatClassifierServicer):

    def __init__(self):
        logger.debug('initialising chitchat servicer')
        self.chitchat_classifier = DefaultChitChatClassifier()

    def classify_chitchat(self, request: ChitChatRequest, context) -> ChitChatResponse:
       return self.chitchat_classifier.classify_chitchat(request)
