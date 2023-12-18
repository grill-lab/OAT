import os
from .abstract_qa import AbstractQA

from taskmap_pb2 import Session
import grpc

from utils import logger
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList
from qa_pb2_grpc import TaskQuestionAnsweringStub


class IntraTaskmapQA(AbstractQA):

    def __init__(self, environ_var: str):
        self.endpoint_var = environ_var
        channel = grpc.insecure_channel(os.environ.get(environ_var))
        self.intra_taskmap_qa_stub = TaskQuestionAnsweringStub(channel)
    
    def rewrite_query(self, session: Session) -> QAQuery:

        try:
            query = self.intra_taskmap_qa_stub.rewrite_query(session)
        except grpc.RpcError:
            query: QAQuery = QAQuery()
            logger.warning("IntraTaskmap QA Endpoint did not respond")
        
        return query
    
    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        pass
    
    def synth_response(self, request: QARequest) -> QAResponse:

        try:
            response = self.intra_taskmap_qa_stub.synth_response(request)
        except grpc.RpcError:
            response: QAResponse = QAResponse()
            logger.warning("IntraTaskmap QA  Endpoint did not respond.")
        
        return response
