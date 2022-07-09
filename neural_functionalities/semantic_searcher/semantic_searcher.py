import os
import re
from .abstract_semantic_searcher import AbstractSemanticSearcher
from semantic_searcher_pb2 import SemanticQuery, ThemeDocument, ThemeMapping

from sentence_transformers import SentenceTransformer, util
import json
import torch
from google.protobuf.json_format import Parse
from utils import logger, ProtoDB
import time
import threading
from database_pb2_grpc import DatabaseStub
from database_pb2 import Void
import grpc

class SemanticSearcher(AbstractSemanticSearcher):

    def __init__(self) -> None:
        self.embedder = SentenceTransformer(
            'all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling"
        )

        channel = grpc.insecure_channel(os.environ.get("EXTERNAL_FUNCTIONALITIES_URL"))
        self.database = DatabaseStub(channel)

        self.lock = threading.Lock()
        self.__generate_embeddings()

    def __get_queries(self):
        response = self.database.get_queries(Void())
        return list(response.queries)

    def __generate_embeddings(self):
        logger.info('Computing query embeddings for Themes...')

        query_list = self.__get_queries()
        if len(query_list) == 0:
            logger.info("No Theme Queries")
            self.query_list = []
            return
        queries_embeddings = self.embedder.encode(query_list, convert_to_tensor=True)
        self.query_list = query_list
        self.queries_embeddings = queries_embeddings
        logger.info('Theme Query computations completed')

    @staticmethod
    def __rank_corpus(query_embedding, corpus_embeddings):

        similarity_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]
        scores, idxs = torch.topk(similarity_scores, k=1)

        return scores, idxs

    def __check_queries_changes(self):
        # Grants that the check is atomic, so that we don't run it multiple times in parallel
        with self.lock:
            query_list = self.__get_queries()
            if set(query_list) != set(self.query_list):
                logger.info("DETECTED CHANGE, RELOADING THEME QUERIES!")
                self.__generate_embeddings()

    def search_theme(self, query: SemanticQuery) -> ThemeMapping:

        matched_theme = ThemeMapping()
        if len(self.query_list) == 0:
            return matched_theme

        query_embedding = self.embedder.encode(query.text, convert_to_tensor=True)

        # this does not make the operation thread-safe, but it should avoid problems in most situations
        while self.lock.locked():
            time.sleep(0.01)

        try:
            # compute similarities
            scores, idxs = self.__rank_corpus(query_embedding, self.queries_embeddings)

            for count, (score, q_idx) in enumerate(zip(scores, idxs)):
                if count == 0 and score > 0.7:
                    request = ThemeMapping()
                    request.theme_query = self.query_list[q_idx]
                    response = self.database.get_theme(request)
                    matched_theme = response
                    logger.info(
                        f"RELEVANT QUERY: {self.query_list[q_idx]} <-> Score: {score})"
                    )
                else:
                    logger.info(
                        f"IRRELEVANT QUERY: {self.query_list[q_idx]} <-> Score: {score})"
                    )
        except Exception as e:
            logger.warning("Theme Query Matching Failed!", exc_info=e)

        # Asynchronously check if queries need to be reloaded
        thread = threading.Thread(target=self.__check_queries_changes)
        thread.start()

        return matched_theme


