import os
import grpc
from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session
from dangerous_task_pb2_grpc import DangerousStub


class DangerousQueryParser(AbstractParser):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.__parser = DangerousStub(channel)

    def __call__(self, session: Session) -> Session:
        dangerous_assessment = self.__parser.dangerous_query_check(session)

        if dangerous_assessment.is_dangerous:
            session.turn[-1].user_request.interaction.intents.append("DangerousQueryIntent")

        return session
