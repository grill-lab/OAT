from qa_pb2_grpc import QuestionAnsweringServicer, add_QuestionAnsweringServicer_to_server
from taskmap_pb2 import Session
from qa_pb2 import *

from . import AbstractQA
from utils import init
from qa.config import qa_config


class Servicer(QuestionAnsweringServicer):

    def __init__(self):
        self.qa_system: AbstractQA = init(qa_config)

    def rewrite_query(self, session: Session, context) -> QAQuery:
        return self.qa_system.rewrite_query(session)

    def domain_retrieve(self, query: QAQuery, context) -> DocumentList:
        return self.qa_system.domain_retrieve(query)

    def synth_response(self, request: QARequest, context) -> QAResponse:
        return self.qa_system.synth_response(request)