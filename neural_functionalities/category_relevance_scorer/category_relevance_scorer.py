import torch

from category_retrieval_pb2 import CategorySearchResult
from offline_pb2 import CategoryDocument
from sentence_transformers import SentenceTransformer, util
from utils import logger


def order_subcategories(matched_category, idxs) -> CategoryDocument:
    ordered_categories = []
    for idx in range(len(matched_category.sub_categories)):
        if idx in idxs:
            ordered_categories.append(matched_category.sub_categories[idx])
    del matched_category.sub_categories[:]
    matched_category.sub_categories.extend(ordered_categories)
    return matched_category


class CategoryRelevanceScorer:

    def __init__(self) -> None:
        self.embedder = SentenceTransformer(
            'all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling"
        )
        self.query_list = []

    def score_categories(self, search_result: CategorySearchResult) -> CategoryDocument:

        logger.info('Category searching!')

        matched_category = CategoryDocument()
        if len(search_result.results) < 3:
            return matched_category

        queries_embeddings = self.__generate_embeddings(search_result)
        query_embedding = self.embedder.encode(search_result.original_query_text, convert_to_tensor=True)

        try:
            # compute similarities
            scores, idxs = self.__rank_corpus(query_embedding, queries_embeddings, top_k = 1)

            for count, (score, q_idx) in enumerate(zip(scores, idxs)):
                if count == 0 and score > .7:
                    matched_category = search_result.results[q_idx]
                    logger.info(
                        f"RELEVANT CATEGORY: {search_result.results[q_idx].title} <-> Score: {score})"
                    )
                else:
                    logger.info(
                        f"IRRELEVANT CATEGORY: {search_result.results[q_idx].title} <-> Score: {score})"
                    )
                    return matched_category
        except Exception as e:

            logger.warning("Category Query Matching Failed!", exc_info=e)

        if len(matched_category.sub_categories) < 3:
            empty_result = CategoryDocument()
            return empty_result

        category_embeddings = self.__sub_embeddings(matched_category)
        scores, idxs = self.__rank_corpus(query_embedding, category_embeddings, top_k=3)

        matched_category = order_subcategories(matched_category, idxs)

        return matched_category

    def __sub_embeddings(self, matched_category: CategoryDocument):
        sub_titles = []
        for sub in matched_category.sub_categories:
            sub_titles.append(sub.title)
        return self.embedder.encode(sub_titles, convert_to_tensor=True)
            
    def __generate_embeddings(self, search_result: CategorySearchResult):
        logger.info('Computing query embeddings for Categories...')

        query_list = [candidate.title for candidate in search_result.results]
        if len(query_list) == 0:
            logger.info("No Category Queries Found")
            self.query_list = []
            return
            
        queries_embeddings = self.embedder.encode(query_list, convert_to_tensor=True)
        self.query_list = query_list
        logger.info(f'query list: {query_list}')
        logger.info('Category Query computations completed')
        return queries_embeddings

    @staticmethod
    def __rank_corpus(query_embedding, corpus_embeddings, top_k):

        similarity_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]
        scores, idxs = torch.topk(similarity_scores, k=top_k)

        return scores, idxs




