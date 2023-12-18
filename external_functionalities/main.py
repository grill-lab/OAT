import grpc
from concurrent import futures

from offensive_speech_classifier import Servicer as Offensive_Speech_Servicer
from offensive_speech_classifier import add_to_server as add_offensive_speech_to_server

from database import Servicer as DB_Servicer
from database import add_to_server as add_db_to_server

from dangerous_task import Servicer as Dangerous_Servicer
from dangerous_task import add_to_server as add_dangerous_to_server

from response_relevance_classifier import Servicer as Response_Relevance_Servicer
from response_relevance_classifier import add_to_server as add_response_relevance_classifier_to_server

from utils import get_interceptors


def serve():
    interceptors = get_interceptors()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=interceptors)

    add_offensive_speech_to_server(Offensive_Speech_Servicer(), server)
    add_dangerous_to_server(Dangerous_Servicer(), server)
    add_db_to_server(DB_Servicer(), server)
    add_response_relevance_classifier_to_server(Response_Relevance_Servicer(), server)

    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()