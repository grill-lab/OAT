from chitchat_classifier_pb2 import ChitChatRequest, ChitChatResponse
from .abstract_chitchat_classifier import AbstractChitChatClassifier

from sentence_transformers import SentenceTransformer, util

from utils import (
    CHITCHAT_TUPLE, logger, CHITCHAT_GREETINGS
)


class ChitChatClassifier(AbstractChitChatClassifier):
    def __init__(self):
        logger.info('loading Chit Chat Classifier...')
        self.model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling")
        self.prompt_embeddings = []
        CHITCHAT_TUPLE.extend(CHITCHAT_GREETINGS)
        self.responses = [pair[1] for pair in CHITCHAT_TUPLE]
        self.prompt_embeddings = self.model.encode([pair[0] for pair in CHITCHAT_TUPLE], convert_to_tensor=True)
        logger.info('Loaded Chit Chat Classifier')

    def classify_chitchat(self, request: ChitChatRequest) -> ChitChatResponse:
        response: ChitChatResponse = ChitChatResponse()
        user_chit_chat: str = request.text

        text_embedding = self.model.encode(user_chit_chat, convert_to_tensor=True)

        similarity_scores = util.cos_sim(text_embedding, self.prompt_embeddings)[0]
        sorted_idxs = similarity_scores.argsort(descending=True)
        scores = similarity_scores[sorted_idxs].tolist()
        best_match_score = scores[0]
        best_match_idx = sorted_idxs[0]

        logger.info(f'BEST MATCH: {self.responses[best_match_idx]} with score {best_match_score}')

        if best_match_score > request.threshold:
            response.text = self.responses[best_match_idx]
        else:
            logger.info(f'All chit chat responses are below the threshold of {request.threshold}')
        
        return response
