from searcher_pb2 import SearchQuery, ThemeQuery

import random

from utils import theme_recommendations


class ThemeBuilder:

    def __init__(self):
        self.theme_recommendations = theme_recommendations
        self.query_images = {}


    def theme_query_recommendation(self, theme_query: ThemeQuery) -> SearchQuery:
        """ Build a SearchQuery based on themes. """
        # Unpack theme query.
        themes = theme_query.themes
        top_k = theme_query.top_k
        domain = theme_query.domain
        headless = theme_query.headless

        search_query = SearchQuery()

        # Filter for valid themes.
        themes_confirmed = [t for t in themes if t in self.theme_recommendations]

        # Return blank SearchQuery if no valid themes.
        if not themes_confirmed:
            return search_query

        # Randomly select a single theme query (if multiple)
        theme_queries = []
        for theme in themes_confirmed:
            theme_queries.append(self.theme_recommendations[theme])
        random.shuffle(theme_queries)
        theme_query = theme_queries[0]

        # Build theme SearchQuery
        search_query: SearchQuery = SearchQuery()
        search_query.text = theme_query
        search_query.last_utterance = theme_query
        search_query.domain = domain
        search_query.headless = headless
        search_query.top_k = top_k

        return search_query