from taskmap_pb2 import Session
from searcher_pb2 import SearchQuery
from utils import NUM_SEARCH_RESULTS


class QueryBuilder:

    def synthesize_query(self, session: Session) -> SearchQuery:
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

