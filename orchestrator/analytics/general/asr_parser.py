import os
import grpc
from ..abstract_parser import AbstractParser

from asr_parser_pb2_grpc import ASRParserStub
from asr_parser_pb2 import ASRResponse
from taskmap_pb2 import Session


class ASRParser(AbstractParser):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.asr_service = ASRParserStub(channel)

    def __call__(self, session: Session) -> Session:

        response: ASRResponse = self.asr_service.rerank(session)

        # Disable the use of the ASR Reranking for the initial roll out
        # if response.utterance != '':
        #     session.turn[-1].user_request.interaction.text = response.utterance

        return session
