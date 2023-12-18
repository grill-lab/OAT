from joke_retriever_pb2_grpc import JokeRetrieverServicer, add_JokeRetrieverServicer_to_server
from taskmap_pb2 import ExtraInfo

from . import DefaultJokeRetriever


class Servicer(JokeRetrieverServicer):

    def __init__(self):
        self.joke_retriever = DefaultJokeRetriever()

    def get_random_joke(self, request, context) -> ExtraInfo:
        return self.joke_retriever.get_random_joke()
