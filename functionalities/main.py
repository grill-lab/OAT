import grpc
from concurrent import futures

from task_manager import Servicer as TM_Servicer
from task_manager import add_to_server as add_tm_to_server

from searcher import Servicer as Searcher_Servicer
from searcher import add_to_server as add_search_to_server

from intent_classifier import Servicer as Intent_Servicer
from intent_classifier import add_to_server as add_intent_to_server

from safety_check import Servicer as Safety_Servicer
from safety_check import add_to_server as add_safety_to_server

from dangerous_task import Servicer as Dangerous_Servicer
from dangerous_task import add_to_server as add_dangerous_to_server

from personality import Servicer as Personalilty_Servicer
from personality import add_to_server as add_personality_to_server

# from qa import Servicer as QA_Servicer
# from qa import add_to_server as add_qa_to_server

from query_builder import Servicer as QueryBuilderServicer
from query_builder import add_to_server as add_query_builder_to_servicer

from action_method_classifier import Servicer as ActionClassifier_Servicer
from action_method_classifier import add_to_server as add_action_classifier_to_server

from utils import get_server_interceptor, logger


def serve():
    interceptor = get_server_interceptor()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=(interceptor,))

    add_tm_to_server(TM_Servicer(), server)
    add_search_to_server(Searcher_Servicer(), server)
    add_intent_to_server(Intent_Servicer(), server)
    add_safety_to_server(Safety_Servicer(), server)
    add_dangerous_to_server(Dangerous_Servicer(), server)
    add_personality_to_server(Personalilty_Servicer(), server)
    # add_qa_to_server(QA_Servicer(), server)
    add_query_builder_to_servicer(QueryBuilderServicer(), server)
    # add_action_classifier_to_server(ActionClassifier_Servicer(), server)

    logger.info('Finished loading all models')

    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
