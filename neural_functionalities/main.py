import grpc
from concurrent import futures

from phase_intent_classifier import (
    Servicer as Phase_Intent_Classifier_Servicer,
    add_to_server as add_phase_intent_classifier_to_server,
)
from utils import logger

from task_qa import Servicer as Task_QA_Servicer
from task_qa import add_to_server as add_task_qa_to_server

from general_qa import Servicer as General_QA_Servicer
from general_qa import add_to_server as add_general_qa_to_server

# from sentence_scoring import Servicer as SentenceScoring_Servicer
# from sentence_scoring import add_to_server as add_sentence_scorer_to_server

from taskmap_scorer import Servicer as Scorer_Servicer
from taskmap_scorer import add_to_server as add_scorer_to_server

# from mlm_scoring import (
#     Servicer as MLM_Scorer_Servicer,
#     add_to_server as add_mlm_scorer_to_server
# )

from category_relevance_scorer import (
    Servicer as Category_Relevance_Scorer,
    add_to_server as add_category_relevance_to_server
)

from semantic_searcher import (
    Servicer as Semantic_Searcher_Servicer,
    add_to_server as add_semantic_searcher_to_server
)

from video_searcher import (
    Servicer as Video_Searcher_Servicer,
    add_to_server as add_video_searcher_to_server
)

from chitchat_classifier import (
    Servicer as ChitChatServicerClassifer,
    add_to_server as add_chit_chat_to_server
)

# from query_searcher import (
#     Servicer as QuerySearchServicer,
#     add_to_server as add_query_search_to_server
# )

from utils import get_interceptors


def serve():
    interceptors = get_interceptors()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )

    add_task_qa_to_server(Task_QA_Servicer(), server)
    add_general_qa_to_server(General_QA_Servicer(), server)
    add_phase_intent_classifier_to_server(Phase_Intent_Classifier_Servicer(), server)
    add_scorer_to_server(Scorer_Servicer(), server)
    # add_mlm_scorer_to_server(MLM_Scorer_Servicer(), server)
    # add_sentence_scorer_to_server(SentenceScoring_Servicer(), server)
    add_semantic_searcher_to_server(Semantic_Searcher_Servicer(), server)
    add_video_searcher_to_server(Video_Searcher_Servicer(), server)
    add_chit_chat_to_server(ChitChatServicerClassifer(), server)
    # add_query_search_to_server(QuerySearchServicer(), server)

    add_category_relevance_to_server(Category_Relevance_Scorer(), server)

    logger.info('Finished loading all models')

    server.add_insecure_port("[::]:8000")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
