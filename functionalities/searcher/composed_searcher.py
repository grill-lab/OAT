
from searcher_pb2 import SearchQuery, TaskMapList, SearchResults, SearchLog
from taskmap_pb2 import Session
from searcher_pb2_grpc import ScoreTaskMapStub
from image_searcher_pb2 import ImageRequest
from image_searcher_pb2_grpc import ImageSearcherStub

from .abstract_searcher import AbstractSearcher
from typing import List, Any, Tuple
from concurrent.futures import TimeoutError, ThreadPoolExecutor
import time
from utils import logger, init, indri_stop_words, timeit
from pyserini.analysis import Analyzer, get_lucene_analyzer
from database_pb2_grpc import DatabaseStub
from .filter import filter_taskmap, filter_wikihow_cooking

import grpc
import os
import random


class ComposedSearcher(AbstractSearcher):

    def __init__(self, classes_list: List[Any], timeout: int, workers: int = 0):
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.neural_scorer = ScoreTaskMapStub(neural_channel)
        self.image_searcher = ImageSearcherStub(neural_channel)
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

    def __processing(self, sentence: str):
        """ process queries or sections of documents by removing stopwords before sharding / stemming. """
        words = self.word_tokenizer.analyze(sentence)
        new_sentence = " ".join([w for w in words if w not in indri_stop_words])
        return self.analyzer.analyze(new_sentence)

    @timeit
    def retrieval(self, query: SearchQuery) -> List[Tuple[TaskMapList, str]]:
        """ Access initial indexes based on query. """

        top_k = query.top_k
        query.top_k = 9
        # --- multi-thread to access several searchers at same time ---
        tic = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self.workers or len(self.searchers_list)) as executor:

            def _search_wrapper(thread_searcher: AbstractSearcher, local_query: SearchQuery):
                return thread_searcher.search_taskmap(local_query)
            futures = [executor.submit(_search_wrapper, searcher, query) for searcher in self.searchers_list]

            timeout: float = self.timeout / 1000 + time.monotonic()
            searcher_taskmap_lists: list = []
            for future, searcher in zip(futures, self.searchers_list):
                try:
                    if future.done() or timeout - time.monotonic() > 0:
                        searcher_taskmap_list = future.result(timeout=timeout - time.monotonic())
                        searcher_taskmap_lists.append((searcher_taskmap_list.taskmap_list, type(searcher).__name__))
                        toc = time.perf_counter()
                        logger.info(f"All search time: {toc - tic:0.4f} seconds")
                        logger.info(f'{type(searcher).__name__}: Found {len(searcher_taskmap_list.taskmap_list.candidates)} candidates TaskMaps in {toc - tic:0.4f} seconds ')
                    else:
                        future.cancel()
                        logger.warning(f"Timeout for searcher: {type(searcher).__name__}")

                except TimeoutError:
                    future.cancel()
                    logger.warning(f"Timeout with error for searcher: {type(searcher).__name__}")
                    continue

            query.top_k = top_k
            final_taskmap_list: TaskMapList = TaskMapList()
            for taskmap_list, searcher_name in searcher_taskmap_lists:
                for taskmap in taskmap_list.candidates:
                    if filter_taskmap(taskmap) and filter_wikihow_cooking(query, taskmap):
                        final_taskmap_list.candidates.append(taskmap)
                logger.info(f"Filtered TaskMaps for {searcher_name}: {len(final_taskmap_list.candidates)}")

            # Search logs
            search_log = SearchLog()
            search_log.search_query.MergeFrom(query)
            search_log.id = query.session_id + "_" + query.turn_id
            self.db.save_search_logs(search_log)

            # Search results
            search_results = SearchResults()
            search_results.taskmap_list.MergeFrom(final_taskmap_list)
            search_results.search_log.MergeFrom(search_log)

        return search_results

    def augment_taskmap_images(self, taskmap, query):

        # -- Thumbnail --
        if len(taskmap.thumbnail_url) == 0:
            # make default
            image_request = ImageRequest()
            image_request.query = taskmap.title
            image_request.k = 1
            image = self.image_searcher.search_image(image_request)
            if image.path != "":
                taskmap.thumbnail_url = image.path
            else:
                default_cooking = [f'https://grill-bot-data.s3.amazonaws.com/images/cooking-{i}.jpg' for i in range(1,17)]
                default_diy = [f'https://grill-bot-data.s3.amazonaws.com/images/diy-{i}.jpg' for i in range(1,8)]
                
                if query.domain == Session.Domain.COOKING:
                    taskmap.thumbnail_url = random.choice(default_cooking)
                else:
                    taskmap.thumbnail_url = random.choice(default_diy)

        return taskmap

    @timeit
    def search_taskmap(self, query: SearchQuery) -> TaskMapList:
        """ Retrieval across multiple searchers """

        # Retrieval
        searcher_taskmap_lists = self.retrieval(query)

        return searcher_taskmap_lists
