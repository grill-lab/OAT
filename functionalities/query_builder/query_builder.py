from taskmap_pb2 import Session
from searcher_pb2 import SearchQuery, UserUtterance, ProcessedString
from pyserini.analysis import Analyzer, get_lucene_analyzer
from utils import NUM_SEARCH_RESULTS, indri_stop_words, VAGUE_WORDS, logger


class QueryBuilder:

    def __init__(self):
        self.word_tokenizer = Analyzer(get_lucene_analyzer(stemming=False, stopwords=False))
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))

    @staticmethod
    def synthesize_query(session: Session) -> SearchQuery:
        search_query: SearchQuery = SearchQuery()
        # Query the last session.task_selection.elicitation_count sentences
        text = ""
        for utterance in session.task_selection.elicitation_utterances:
            text += utterance + '. '

        # Arguments use in search for logging purposes
        search_query.session_id = session.session_id
        search_query.turn_id = session.turn[-1].id

        search_query.text = text
        search_query.last_utterance = session.task_selection.elicitation_utterances[-1]
        search_query.top_k = NUM_SEARCH_RESULTS
        search_query.domain = session.domain
        search_query.headless = session.headless
        return search_query

    def processing_utterance(self, utterance: UserUtterance) -> ProcessedString:
        words = self.word_tokenizer.analyze(utterance.text)
        new_sentence = " ".join([w for w in words if w.lower() not in indri_stop_words and
                                 w.lower() not in VAGUE_WORDS])
        processed_str = ProcessedString()
        text = " ".join(self.analyzer.analyze(new_sentence))
        processed_str.text = text
        return processed_str

