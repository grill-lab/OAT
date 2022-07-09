import grpc
from concurrent import futures

from offensive_speech_classifier import Servicer as Offensive_Speech_Servicer
from offensive_speech_classifier import add_to_server as add_offensive_speech_to_server

from database import Servicer as DB_Servicer
from database import add_to_server as add_db_to_server

from utils import get_server_interceptor

def serve():
    interceptor = get_server_interceptor()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=(interceptor,))

    add_offensive_speech_to_server(Offensive_Speech_Servicer(), server)
    add_db_to_server(DB_Servicer(), server)

    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()