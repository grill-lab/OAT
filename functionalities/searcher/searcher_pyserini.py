from taskmap_pb2 import Session
from .abstract_searcher import AbstractSearcher
from searcher_pb2 import SearchQuery, SearchResults, TaskMapList
from pyserini.search.lucene import LuceneSearcher

import json
import os
from google.protobuf.json_format import Parse
from utils import get_file_system


class SearcherPyserini(AbstractSearcher):

    def __init__(self, index_path, dense_index_path=""):
        index_path = os.path.join(get_file_system(), index_path)
        self.searcher = LuceneSearcher(index_dir=index_path)
        self.dense = False

        if dense_index_path:
            from pyserini.search.faiss import FaissSearcher
            from pyserini.search.hybrid import HybridSearcher

            self.dense = True
            dense_index_path = os.path.join(get_file_system(), dense_index_path)
            self.custom_searcher_dense = FaissSearcher(
                dense_index_path, 'castorini/ance-msmarco-passage'
            )
            
            self.hybrid_searcher = HybridSearcher(self.custom_searcher_dense, self.searcher)

    def search_taskmap(self, query: SearchQuery) -> SearchResults:

        taskmap_list = TaskMapList()

        top_k = query.top_k
        docs = []

        # Hybrid
        if self.dense:
            hits = self.hybrid_searcher.search(
                query=query.last_utterance, k0=top_k, k=top_k, alpha=0.4, normalization=True
            )
        else:
            hits = self.searcher.search(q=query.last_utterance, k=top_k)

        for hit in hits:
            doc = self.searcher.doc(docid=hit.docid)
            docs.append(doc.raw())

        for doc_string in docs:
            doc_json = json.loads(doc_string)
            taskmap_json = doc_json['recipe_document_json']
            obj = taskmap_list.candidates.add()
            Parse(json.dumps(taskmap_json), obj)

        taskmap_list = self.filter_dangerous_tasks(taskmap_list=taskmap_list, top_k=top_k)

        search_results = SearchResults()
        search_results.taskmap_list.MergeFrom(taskmap_list)

        return search_results
