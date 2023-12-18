import os
import json
import sys

from pyserini.search.lucene import LuceneSearcher
from google.protobuf.json_format import Parse
from compiled_protobufs.video_document_pb2 import VideoDocument
from utils import get_file_system

sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')


class VideoSearcher:

    def __init__(self, video_index_path, video_dense_index_path=""):
        index_path = os.path.join(get_file_system(), video_index_path)
        self.searcher = LuceneSearcher(index_dir=index_path)
        self.dense = False

        if video_dense_index_path:
            from pyserini.search.faiss import FaissSearcher
            from pyserini.search.hybrid import HybridSearcher

            self.dense = True
            dense_index_path = os.path.join(get_file_system(), video_dense_index_path)
            self.custom_searcher_dense = FaissSearcher(
                dense_index_path, 'castorini/ance-msmarco-passage'
            )

            self.hybrid_searcher = HybridSearcher(self.custom_searcher_dense, self.searcher)

    def search_video(self, query: str) -> VideoDocument:

        top_k = 1
        docs = []

        # Hybrid
        if self.dense:
            hits = self.hybrid_searcher.search(
                query=query, k0=top_k, k=top_k, alpha=0.4, normalization=True
            )
        else:
            hits = self.searcher.search(q=query, k=top_k)

        for hit in hits:
            doc = self.searcher.doc(docid=hit.docid)
            docs.append(doc.raw())

        for doc_string in docs[:top_k]:
            doc_json = json.loads(doc_string)
            taskmap_json = doc_json['document_json']
            return Parse(json.dumps(taskmap_json), VideoDocument())
