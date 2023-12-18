import os
import json
import grpc

from utils import logger, get_file_system, indri_stop_words
from category_retrieval_pb2 import CategoryQuery, CategorySearchResult
from offline_pb2 import CategoryDocument
from category_retrieval_pb2_grpc import CategoryScorerStub

from pyserini.search.lucene import LuceneSearcher
from pyserini.analysis import Analyzer, get_lucene_analyzer
from google.protobuf.json_format import Parse


class CategorySearcher:

    def __init__(self):
        objects_path = os.path.join(get_file_system(), 'offline/category_index/objects_idx')
        if os.path.isdir(objects_path):
            self.category_retriever = LuceneSearcher(index_dir=objects_path)
        self.word_tokenizer = Analyzer(get_lucene_analyzer(stemming=False, stopwords=False))
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))

        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.neural_scorer = CategoryScorerStub(neural_channel)

    def processing(self, sentence: str):
        """ process queries or sections of documents by removing stopwords before sharding / stemming. """
        words = self.word_tokenizer.analyze(sentence)
        new_sentence = " ".join([w for w in words if w not in indri_stop_words])
        return " ".join(self.analyzer.analyze(new_sentence))

    def search_category(self, query: CategoryQuery) -> CategoryDocument:

        top_k = query.top_k
        hits = self.category_retriever.search(q=self.processing(query.text), k=top_k)

        search_result = CategorySearchResult()
        search_result.original_query_text = query.text
        for hit in hits:
            doc = self.category_retriever.doc(hit.docid)
            doc_json = json.loads(doc.raw())
            category_json = doc_json['category_document_json']
            search_result.results.append(Parse(json.dumps(category_json), CategoryDocument()))
        final_result = self.neural_scorer.score_categories(search_result)

        logger.info(f'Matched and relevant category: {final_result}')

        return final_result
