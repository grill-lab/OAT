import os

import grpc

from taskmap_pb2 import Session
from searcher_pb2_grpc import SearcherStub
from searcher_pb2 import SearchQuery

from utils import logger


def create_query(domain, text) -> SearchQuery:
    query: SearchQuery = SearchQuery()
    query.session_id = "session_id"
    query.turn_id = "turn_id"
    query.text = text
    query.last_utterance = text
    query.top_k = 100
    if domain == "cooking":
        query.domain = Session.Domain.COOKING
    else:
        query.domain = Session.Domain.DIY
    query.headless = False
    return query


def test_search():
    channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
    searcher = SearcherStub(channel)
    # query_builder = QueryBuilderStub(channel)

    dummy_queries = [
        # ("DIY", "how do I hang a picture frame"),
        # ("cooking", "How do I make a cake"),
        # ("DIY", "make a toy boat"),
        # ("cooking", "baked alaska"),
        # ("cooking", "sand castle"),
        # ("DIY", "doll house"),
        # ("cooking", "how do I make mac and cheese"),
        # ("cooking", "lemonade"),
        # ("cooking", "How to make an omelette"),
        ("cooking", "Potatoes"),
    ]

    for domain, text in dummy_queries:
        query = create_query(domain=domain, text=text)
        search_results = searcher.search_taskmap(query)
        candidates = search_results.taskmap_list.candidates  # difference between text and last_utterance???
        if len(candidates) > 3:
            candidates = candidates[:20]
            logger.info(f"--- Found matches for: {domain}, {text} ---")
            for idx, candidate in enumerate(candidates):
                logger.info(f"Match {idx+1}: {candidate.title}")
        else:
            logger.info(f"Did not find 3 matches for: {domain}, {text}")
    # assert True != True
