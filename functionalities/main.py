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

from personality import Servicer as Personalilty_Servicer
from personality import add_to_server as add_personality_to_server

from qa import Servicer as QA_Servicer
from qa import add_to_server as add_qa_to_server

from query_builder import Servicer as QueryBuilderServicer
from query_builder import add_to_server as add_query_builder_to_servicer

from action_method_classifier import Servicer as ActionClassifier_Servicer
from action_method_classifier import add_to_server as add_action_classifier_to_server

from category_searcher import Servicer as CategorySearcher_Servicer
from category_searcher import add_to_server as add_category_searcher_to_server

from joke_retriever import Servicer as JokeRetrieverServicer
from joke_retriever import add_to_server as add_joke_retriever_to_server

from llm_chit_chat import (
    Servicer as LLM_ChitChat_Servicer,
    add_to_server as add_llm_chitchat_to_server
)

from llm_description_generation import (
    Servicer as LLM_DescriptionGeneration_Servicer,
    add_to_server as add_llm_description_generation_to_server
)

from llm_proactive_question_generation import (
    Servicer as LLM_ProActiveQuestionGeneration_Servicer,
    add_to_server as add_llm_proactive_question_generation_to_server
)

from llm_summary_generation import (
    Servicer as LLM_SummaryGeneration_Servicer,
    add_to_server as add_llm_summary_generation_to_server
)

from execution_search_manager import (
    Servicer as LLM_ExecutionSearchManager_Servicer,
    add_to_server as add_llm_execution_search_manager_to_server
)

from llm_ingredient_substitution import (
    Servicer as LLm_IngredientSubstitution_Servicer,
    add_to_server as add_llm_ingredient_substitution_to_server
)

from utils import logger, get_interceptors


def serve():
    interceptors = get_interceptors()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=interceptors)

    add_tm_to_server(TM_Servicer(), server)
    add_search_to_server(Searcher_Servicer(), server)
    add_intent_to_server(Intent_Servicer(), server)
    add_safety_to_server(Safety_Servicer(), server)
    add_personality_to_server(Personalilty_Servicer(), server)
    add_qa_to_server(QA_Servicer(), server)
    add_query_builder_to_servicer(QueryBuilderServicer(), server)
    add_action_classifier_to_server(ActionClassifier_Servicer(), server)
    add_category_searcher_to_server(CategorySearcher_Servicer(), server)
    add_llm_summary_generation_to_server(LLM_SummaryGeneration_Servicer(), server)
    add_llm_chitchat_to_server(LLM_ChitChat_Servicer(), server)
    add_joke_retriever_to_server(JokeRetrieverServicer(), server)
    add_llm_description_generation_to_server(LLM_DescriptionGeneration_Servicer(), server)
    add_llm_proactive_question_generation_to_server(LLM_ProActiveQuestionGeneration_Servicer(), server)
    add_llm_execution_search_manager_to_server(LLM_ExecutionSearchManager_Servicer(), server)
    add_llm_ingredient_substitution_to_server(LLm_IngredientSubstitution_Servicer(), server)

    logger.info('Finished loading all models')

    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
