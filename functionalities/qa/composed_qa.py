import os
import grpc
import time
import random

from .abstract_qa import AbstractQA
from taskmap_pb2 import Session

from utils import (
    logger, init, jaccard_sim, DEFAULT_QA_PROMPTS, get_helpful_prompt
)
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList

from typing import List, Any, Tuple
from concurrent.futures import TimeoutError, ThreadPoolExecutor

from qa_response_relevance_pb2_grpc import ResponseRelevanceStub
from qa_response_relevance_pb2 import AssessmentRequest

from pyserini.analysis import Analyzer, get_lucene_analyzer

from .substitution_helper import SubstitutionHelper


class ComposedQA(AbstractQA):

    def __init__(self, classes_list: List[Any], timeout: int, workers: int = 0):

        self.workers = workers
        self.timeout: int = timeout
        self.qa_systems_list = []
        self.analyzer = Analyzer(get_lucene_analyzer())

        for class_config in classes_list:
            assert issubclass(class_config['class'], AbstractQA), \
                "Only Abstract sub-classes can be used"

            self.qa_systems_list.append(init(class_config))

        channel = grpc.insecure_channel(os.environ.get("EXTERNAL_FUNCTIONALITIES_URL"))
        self.response_relevance_client = ResponseRelevanceStub(channel)
        self.substitution_helper = SubstitutionHelper()

    def rewrite_query(self, session: Session) -> QAQuery:
        # all system rewrite in the same way for now, so any system's
        # implementation is fine.
        return self.qa_systems_list[1].rewrite_query(session)
    
    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        pass
    
    def synth_response(self, request: QARequest) -> QAResponse:

        def _process(sentence: str):
            return self.analyzer.analyze(sentence)

        # define the pool of threads that can run asynchronuosly
        # ideally should be equal to the QA systems in use

        start_time = time.time()

        logger.info('Starting to generate answers with thread pool...')
        with ThreadPoolExecutor(max_workers=self.workers or len(self.qa_systems_list)) as executor:

            # function used to make requests
            def _generate_answer(qa_system: AbstractQA, qa_request: QARequest):
                return qa_system.synth_response(qa_request)

            futures = [executor.submit(_generate_answer, qa_system, request)
                       for qa_system in self.qa_systems_list]

            timeout: float = self.timeout / 1000 + time.monotonic()
            llm_timeout = timeout * 1.5
            generated_answers: list = []

            success = False

            for future, qa_system in zip(futures, self.qa_systems_list):
                try:
                    if type(qa_system).__name__ == "LLMQA" and (not success or request.question_type == "chitchat"):
                        timeout = llm_timeout

                    if future.done() or timeout - time.monotonic() > 0:
                        qa_response = future.result(timeout=timeout - time.monotonic())
                        if qa_response.text != "":
                            generated_answers.append((qa_response, type(qa_system).__name__))
                            logger.info(f"{type(qa_system).__name__} generated: {qa_response} in "
                                        f"{time.time() - start_time:.2f}")
                            if type(qa_system).__name__ != "LLMQA" and qa_response.text != "":
                                success = True
                    else:
                        future.cancel()
                        logger.warning(f"Timeout for system: {type(qa_system).__name__}")

                except TimeoutError:
                    future.cancel()
                    logger.warning(f"Timeout with error for system: {type(qa_system).__name__}")
                    continue

        if len(generated_answers) > 0:

            scored_responses = []
            processed_question = _process(request.query.text)

            with ThreadPoolExecutor(max_workers=len(generated_answers)) as executor:
                futures = [executor.submit(self.__score_answer, request.query.text, answer)
                           for answer in generated_answers]
                for future, (response, source) in zip(futures, generated_answers):
                    try:
                        if future.done() or timeout - time.monotonic() > 0:
                            total = future.result(timeout=timeout - time.monotonic())
                            scored_responses.append((response, total))
                        else:
                            future.cancel()
                            total = self.add_qa_type_weights(request.question_type, source)
                            scored_responses.append((response, total))

                    except TimeoutError:
                        future.cancel()
                        total = 0
                        scored_responses.append((response, total))

            for idx, (response, score) in enumerate(scored_responses):
                processed_response = _process(response.text)
                similarity_score = jaccard_sim(processed_question, processed_response)
                scored_responses[idx] = (response, score + similarity_score)

            ranked_responses = sorted(scored_responses, key=lambda x: x[1], reverse=True)

            time_taken = time.time() - start_time
            logger.info(f"QA generation took: {time_taken:.2f}")

            if len(ranked_responses) > 0:
                if len(ranked_responses[0]) > 0:
                    response = ranked_responses[0][0]
                    if request.question_type == "ingredient substitution" and \
                            request.query.phase == QAQuery.TaskPhase.VALIDATING \
                            and request.query.domain == QAQuery.Domain.COOKING:
                        if time_taken < 2:
                            logger.info('We have a substitution question')
                            response = self.substitution_helper.create_substitution_idea(request, response)
                        else:
                            logger.info('We have a substitution question but it took too long to answer')
                        
                    return response  # correct results, everything worked as expected

        logger.info(f'Returning empty response from composed QA')
        empty_response: QAResponse = QAResponse()
        tutorial_list = get_helpful_prompt(phase=request.query.phase, task_title=request.query.taskmap.title,
                                           task_selection=request.query.task_selection, headless=request.headless)
        helpful_prompt = random.choice(tutorial_list)
        empty_response.text = f'{random.sample(DEFAULT_QA_PROMPTS, 1)[0]} {helpful_prompt}'
        return empty_response

    @staticmethod
    def add_qa_type_weights(question_type, qa_system) -> float:
        weights = {
            "LLMQA": {"current task question": 0.2, "current viewing options question": 0.2, "ingredient question": 0.2, 
                      "step question": 0.2, "ingredient substitution": 0.3, "other domain question": 0.3, 
                      "general cooking or DIY question": 0.3, "chit chat": 0.3},
            "IntraTaskmapQA": {"current task question": 0.2, "current viewing options question": 0.2, "ingredient question": 0.2,
                               "step question": 0.1, "ingredient substitution": 0, "other domain question": 0,
                               "general cooking or DIY question": 0, "chit chat": 0},
            "GeneralQA": {"other domain question": 0.2, "general cooking or DIY question": 0.2, "chit chat": 0,
                          "current task question": 0, "current viewing options question": 0, "ingredient question": 0,
                          "step question": 0, "ingredient substitution": 0.1}
        }
        return weights[qa_system][question_type]

    def __score_answer(self, processed_question: str, generated_answer: Tuple[QAResponse, str]) -> float:
        response, source = generated_answer
        if response.text != "":
            assessment_request = AssessmentRequest()
            assessment_request.question = processed_question
            assessment_request.system_response = response.text

            relevance_assessment = self.response_relevance_client.assess_response_relevance(assessment_request)

            if relevance_assessment.is_relevant:
                return relevance_assessment.score
        return 0
        
        


