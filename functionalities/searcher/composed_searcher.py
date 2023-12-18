import grpc
import os
import time

from typing import List, Any
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from pyserini.analysis import Analyzer, get_lucene_analyzer

from utils import logger, init, indri_stop_words
from database_pb2_grpc import DatabaseStub
from .feature_reranker import FeatureReRanker
from searcher_pb2 import SearchQuery, SearchResults, SearchLog, CandidateList, TaskmapIDs, CategoryIDs, CategoryResults
from .abstract_searcher import AbstractSearcher


class ComposedSearcher(AbstractSearcher):

    def __init__(self, classes_list: List[Any], timeout: int, workers: int = 0):
        self.workers = workers
        self.timeout: int = timeout
        self.searchers_list = []
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))
        self.word_tokenizer = Analyzer(get_lucene_analyzer(stemming=False, stopwords=False))

        # Load searchers
        searcher_class: Any
        for class_config in classes_list:
            assert issubclass(class_config['class'], AbstractSearcher), \
                "Only AbstractSearcher child-classes can be used"
            self.searchers_list.append(init(class_config))  # Passing sub_config params

        channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])
        self.db = DatabaseStub(channel)
        self.reranker = FeatureReRanker()

    def __processing(self, sentence: str):
        """ process queries or sections of documents by removing stopwords before sharding / stemming. """
        words = self.word_tokenizer.analyze(sentence)
        new_sentence = " ".join([w for w in words if w not in indri_stop_words])
        return self.analyzer.analyze(new_sentence)

    def retrieval(self, query: SearchQuery) -> SearchResults:
        """ Access initial indexes based on query. """

        top_k = query.top_k
        query.top_k = 50
        # --- multi-thread to access several searchers at same time ---
        tic = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self.workers or len(self.searchers_list)) as executor:

            def _search_wrapper(thread_searcher: AbstractSearcher, local_query: SearchQuery):
                return thread_searcher.search_taskmap(local_query)
            futures = [executor.submit(_search_wrapper, searcher, query) for searcher in self.searchers_list]

            timeout: float = self.timeout / 1000 + time.monotonic()
            searcher_candidate_lists: list = []
            for future, searcher in zip(futures, self.searchers_list):
                try:
                    if future.done() or timeout - time.monotonic() > 0:
                        searcher_candidate_list = future.result(timeout=timeout - time.monotonic())
                        searcher_candidate_lists.append((searcher_candidate_list.candidate_list, type(searcher).__name__))
                        toc = time.perf_counter()
                        logger.info(f"All search time: {toc - tic:0.4f} seconds")
                        logger.info(f'{type(searcher).__name__}: Found '
                                    f'{len(searcher_candidate_list.candidate_list.candidates)} candidates TaskMaps '
                                    f'in {toc - tic:0.4f} seconds ')
                    else:
                        future.cancel()
                        logger.warning(f"Timeout for searcher: {type(searcher).__name__}")

                except TimeoutError:
                    future.cancel()
                    logger.warning(f"Timeout with error for searcher: {type(searcher).__name__}")
                    continue

            query.top_k = top_k
            final_candidate_list: CandidateList = CandidateList()
            for candidate_list, searcher_name in searcher_candidate_lists:
                for union in candidate_list.candidates:
                    final_candidate_list.candidates.append(union)
                logger.info(f"Filtered TaskMaps for {searcher_name}: {len(final_candidate_list.candidates)}")

            # Search logs
            search_log = SearchLog()
            search_log.search_query.MergeFrom(query)
            search_log.id = query.session_id + "_" + query.turn_id
            self.db.save_search_logs(search_log)

            # Search results
            search_results = SearchResults()
            search_results.candidate_list.MergeFrom(final_candidate_list)
            search_results.search_log.MergeFrom(search_log)

        return search_results

    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        """ Retrieval across multiple searchers """

        # Retrieval
        retrieval_search_result = self.retrieval(query)
        # Re-Rank
        reranked_result = self.reranker.re_rank(query, retrieval_search_result)

        return reranked_result

    def retrieve_taskmap(self, ids: TaskmapIDs) -> SearchResults:
        """ Retrieval of taskmaps based on IDs from Pyserini Searcher"""
        return self.searchers_list[0].retrieve_taskmap(ids)
    
    def retrieve_category(self, ids: CategoryIDs) -> CategoryResults:
        """ Retrieval of categories based on IDs from Pyserini Searcher"""
        return self.searchers_list[0].retrieve_category(ids)