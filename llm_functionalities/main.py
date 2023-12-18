import grpc
from concurrent import futures

from utils import logger, get_interceptors

from llm_runner import (
    Servicer as LLM_Runner_Servicer,
    add_to_server as add_llm_runner_to_server
)


def serve():
    interceptors = get_interceptors()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )

    add_llm_runner_to_server(LLM_Runner_Servicer(), server)

    logger.info('Finished loading all LLM functionalities')

    server.add_insecure_port("[::]:8000")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
