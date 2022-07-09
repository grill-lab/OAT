from qa_pb2_grpc import QuestionAnsweringServicer, add_QuestionAnsweringServicer_to_server
from taskmap_pb2 import Session
from qa_pb2 import *

from . import DefaultQA


class Servicer(QuestionAnsweringServicer):

    def __init__(self):
        self.qa = DefaultQA()

    def rewrite_query(self, session: Session, context) -> QAQuery:
        return self.qa.rewrite_query(session)

    def domain_retrieve(self, query: QAQuery, context) -> DocumentList:
        return self.qa.domain_retrieve(query)

    def synth_response(self, request: QARequest, context) -> QAResponse:
        return self.qa.synth_response(request)