from .category_relevance_scorer import CategoryRelevanceScorer as DefaultCategoryRelevanceScorer

from .category_relevance_scorer_servicer import (
    Servicer,
    add_CategoryScorerServicer_to_server as add_to_server
)