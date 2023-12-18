from taskmap_pb2 import TaskMap, TaskmapCategoryUnion
from offline_pb2 import CategoryDocument
from .abstract_searcher import AbstractSearcher
from searcher_pb2 import SearchQuery, SearchResults, UserUtterance, ProcessedString, CandidateList, TaskmapIDs, \
    CategoryIDs, CategoryResults
from searcher_pb2_grpc import QueryBuilderStub

from pyserini.search.lucene import LuceneSearcher
from pyserini.search.hybrid import HybridSearcher
from pyserini.search.faiss import FaissSearcher, TctColBertQueryEncoder

from .abstract_searcher import AbstractSearcher

import json
import os
import grpc
from google.protobuf.json_format import Parse
from utils import get_file_system, logger


class SearcherPyserini(AbstractSearcher):

    def __init__(self, sparse_searcher_path, task_dir, category_dir, dense_index_path=""):
        searcher_path = os.path.join(get_file_system(), sparse_searcher_path)
        task_dir = os.path.join(get_file_system(), task_dir)
        self.searcher = LuceneSearcher(index_dir=searcher_path)
        self.searcher.set_bm25(b=0.4, k1=0.9)
        self.searcher.set_rm3(fb_terms=10, fb_docs=10, original_query_weight=0.5)
        self.taskgraph_retriever = LuceneSearcher(index_dir=task_dir)
        self.category_retriever = LuceneSearcher(index_dir=category_dir)
        self.hybrid = False
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.query_builder = QueryBuilderStub(channel)

        if dense_index_path:
            from pyserini.search.faiss import FaissSearcher
            from pyserini.search.hybrid import HybridSearcher

            self.hybrid = True
            dense_index_path = os.path.join(get_file_system(), dense_index_path)

            encoder = TctColBertQueryEncoder('castorini/tct_colbert-v2-hnp-msmarco')
            self.custom_searcher_dense = FaissSearcher(
                index_dir=dense_index_path,
                query_encoder=encoder,
            )

            self.hybrid_searcher = HybridSearcherOverride(self.custom_searcher_dense, self.searcher)

    def processing(self, sentence: str):
        """ process queries or sections of documents by removing stopwords before sharding / stemming. """
        user_utterance = UserUtterance()
        user_utterance.text = sentence
        processed_str: ProcessedString = self.query_builder.processing_utterance(user_utterance)
        logger.info(f'SEARCH QUERY: {processed_str.text}')
        return processed_str.text

    def search_taskmap(self, query: SearchQuery) -> SearchResults:

        candidate_list = CandidateList()

        top_k = query.top_k
        docs = []

        if self.hybrid:
            hits = self.hybrid_searcher.search(
                query=self.processing(query.last_utterance), k0=top_k, k=top_k,
            )
        else:
            hits = self.searcher.search(q=self.processing(query.last_utterance), k=top_k)

        for hit in hits:
            docid = hit[1] if self.hybrid else hit.docid
            doc = self.taskgraph_retriever.doc(docid=docid)
            doc_type = "TaskMap"
            if doc is None:
                doc = self.category_retriever.doc(docid=docid)
                doc_type = "Category"

            if not doc is None:
                docs.append({"doc_string": doc.raw(), "type": doc_type})

        title_set = set()
        for doc in docs:
            doc_string, doc_type = doc["doc_string"], doc["type"]
            doc_json = json.loads(doc_string)
            union = TaskmapCategoryUnion()
            if doc_type == "TaskMap":
                obj_json = doc_json['document_json']
                obj = TaskMap()
                Parse(json.dumps(obj_json), obj)
                union.task.CopyFrom(obj)
            elif doc_type == "Category":
                obj_json = doc_json['category_document_json']
                obj = CategoryDocument()
                Parse(json.dumps(obj_json), obj)
                union.category.CopyFrom(obj)
            else:
                raise Exception("Neither category nor task in search results.")
            # This should be moved offline
            if obj.title in title_set:
                continue
            title_set.add(obj.title)
            candidate_list.candidates.append(union)

        search_results = SearchResults()
        search_results.candidate_list.MergeFrom(candidate_list)

        return search_results

    def retrieve_taskmap(self, ids: TaskmapIDs) -> SearchResults:

        candidate_list = CandidateList()

        for id in ids.ids:
            doc = self.taskgraph_retriever.doc(docid=id)
            if doc:
                logger.info("DOC FOUND")
                union = TaskmapCategoryUnion()
                obj_json = json.loads(doc.raw())['document_json']
                obj = TaskMap()
                Parse(json.dumps(obj_json), obj)
                union.task.CopyFrom(obj)
                candidate_list.candidates.append(union)
            else:
                logger.info("DOC NOT FOUND")

        search_results = SearchResults()
        search_results.candidate_list.MergeFrom(candidate_list)

        return search_results

    def retrieve_category(self, ids: CategoryIDs) -> CategoryResults:

        category_list = []

        for id in ids.ids:
            doc = self.category_retriever.doc(docid=id)
            if doc:
                obj_json = json.loads(doc.raw())['category_document_json']
                obj = CategoryDocument()
                Parse(json.dumps(obj_json), obj)
                category_list.append(obj)
            else:
                logger.info("Category NOT FOUND")

        category_results = CategoryResults()
        category_results.category.MergeFrom(category_list)

        return category_results


class HybridSearcherOverride(HybridSearcher):
    def search(self, query: str, k0: int = 10, k: int = 10):
        dense_hits = self.dense_searcher.search(query, k0)
        sparse_hits = self.sparse_searcher.search(query, k0)
        trec_runs = [sparse_hits, dense_hits]
        return self.__reciprocal_rank_fusion(trec_runs=trec_runs, k=60, max_docs=k)
        # return self._hybrid_results(dense_hits, sparse_hits, alpha, k, normalization, weight_on_dense)

    @staticmethod
    def __reciprocal_rank_fusion(trec_runs, k=60, max_docs=50):
        """
            Implements a reciprocal rank fusion as define in
            ``Reciprocal Rank fusion outperforms Condorcet and individual Rank Learning Methods`` by Cormack, Clarke and Buettcher.
            Parameters:
                trec_runs: a list of TrecRun objects to fuse
                k: term to avoid vanishing importance of lower-ranked documents. Default value is 60 (default value used in their paper).
                max_docs: maximum number of documents in the final ranking
        """

        doc_scores = {}
        for hits in trec_runs:
            for pos, hit in enumerate(hits, start=1):
                doc_scores[hit.docid] = doc_scores.get(hit.docid, 0.0) + 1.0 / (k + pos)

        # Writes out information for this topic
        merged_run = []
        for (docid, score) in sorted(iter(doc_scores.items()), key=lambda x: (-x[1], x[0]))[:max_docs]:
            merged_run.append([score, docid])

        return merged_run
