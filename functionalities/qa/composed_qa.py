from .abstract_qa import AbstractQA

from taskmap_pb2 import Session
import time

from utils import logger, init, jaccard_sim
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList

from typing import List, Any, Tuple
from concurrent.futures import TimeoutError, ThreadPoolExecutor

import os
import grpc

from qa_response_relevance_pb2_grpc import ResponseRelevanceStub
from qa_response_relevance_pb2 import RelevanceAssessment, AssessmentRequest

from pyserini.analysis import Analyzer, get_lucene_analyzer


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
        
    def rewrite_query(self, session: Session) -> QAQuery:
        # all system rewrite in the same way for now, so any system's
        # implementation is fine.
        return self.qa_systems_list[1].rewrite_query(session)
    
    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        pass
    
    def synth_response(self, request: QARequest) -> QAResponse:

        # define the pool of threads that can run asynchronuosly
        # ideally should be equal to the QA systems in use
        with ThreadPoolExecutor(max_workers=self.workers or len(self.qa_systems_list)) as executor:

            # function used to make requests
            def _generate_answer(qa_system: AbstractQA, qa_request: QARequest):
                return qa_system.synth_response(qa_request)
            
            futures = [executor.submit(_generate_answer, qa_system, request) 
                for qa_system in self.qa_systems_list]
            
            timeout: float = self.timeout/1000 + time.monotonic()
            generated_answers: list = []

            for future, qa_system in zip(futures, self.qa_systems_list):
                try:
                    if future.done() or timeout - time.monotonic() > 0:
                        qa_response = future.result(timeout=timeout - time.monotonic())

                        generated_answers.append((qa_response, type(qa_system).__name__))
                        logger.info("{} generated: {}".format(type(qa_system).__name__, qa_response))
                    else:
                        future.cancel()
                        logger.warning(f"Timeout for system: {type(qa_system).__name__}")

                except TimeoutError:
                    future.cancel()
                    logger.warning(f"Timeout with error for system: {type(qa_system).__name__}")
                    continue
        
        ranked_responses = self.__rank_generated_answers(request.query.text, generated_answers)

        return ranked_responses[0][0]
        
    
    def __rank_generated_answers(self, question: str, 
        generated_answers: List[Tuple[str, str]]) -> QAResponse:

        def _process(sentence: str):
            return self.analyzer.analyze(sentence)

        scored_responses = []
        processed_question = _process(question)

        for response, source in generated_answers:

            assessment_request = AssessmentRequest()
            assessment_request.question = question
            assessment_request.system_response = response.text
            
            relevance_assessment = self.response_relevance_client.assess_response_relevance(assessment_request)
            
            processed_response = _process(response.text)
            similarity_score = jaccard_sim(processed_question, processed_response)

            total = similarity_score

            if relevance_assessment.is_relevant:
                total += relevance_assessment.score

            scored_responses.append((response, total))
        
        ranked_responses = sorted(scored_responses, key=lambda x: x[1], reverse=True)

        for response, score in ranked_responses:
            logger.info("RESPONSE: %s, Score: %.4f" % (response.text, score))

        return ranked_responses
        
        


