import os
import json

from pyserini.search.lucene import LuceneSearcher
from utils import get_file_system


class TranscriptRetriever:

    def __init__(self, transcript_index_path="offline/system_indexes/audio_index"):
        index_path = os.path.join(get_file_system(), transcript_index_path)
        self.searcher = LuceneSearcher(index_dir=index_path)
        self.dense = False

    def retrieve_transcript(self, doc_id):
        result = self.searcher.doc(doc_id)
        if result:
            doc_json = json.loads(result.raw())
            transcript = doc_json['document_json']
            return transcript
