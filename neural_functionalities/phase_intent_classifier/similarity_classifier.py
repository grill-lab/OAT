from sentence_transformers import SentenceTransformer, util
from .abstract_intent_classifier import AbstractClassifier
from utils import logger
import json
from phase_intent_classifier_pb2 import (
    IntentRequest,
    IntentClassification,
)

class NoMatchException(Exception):
    pass

class SimilarityClassifier(AbstractClassifier):

    THRESHHOLD = 0.85

    def __init__(self):

        logger.info('loading and computing intent embeddings')
        self.embedder = SentenceTransformer(
            'all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling"
        )
        self.intents_tree = json.load(open('/shared/models/RinD/single_utterance_classificaitons.json', 'r'))
        self.intents_map = []
        self.utterances = []
        for intent, static_utterances in self.intents_tree.items():
            for utterance in static_utterances:
                self.intents_map.append(intent)
                self.utterances.append(utterance.lower())
        self.utterance_embeddings = self.embedder.encode(self.utterances, convert_to_tensor=True)

    def classify_intent(self,
                        intent_request: IntentRequest
                        ) -> IntentClassification:

        sample = self.preprocess_request(intent_request)

        utter_emb = self.embedder.encode(sample['user'], convert_to_tensor=True)
        similarity_scores = util.cos_sim(utter_emb, self.utterance_embeddings)[0]
        sorted_indexes = similarity_scores.argsort(descending=True)
        sorted_scores = similarity_scores[sorted_indexes]
        passes_threshold = True if sorted_scores[0] > self.THRESHHOLD else False

        if not passes_threshold:
            logger.info(f"No Match found with similarity classifier...")
            raise NoMatchException()

        logger.info(f"Skipping Full RinD since good single intent match")
        intent_string = self.intents_map[sorted_indexes[0]]
        matching_utt = self.utterances[sorted_indexes[0]]
        score = sorted_scores[0]

        logger.info(f"Closest utterance: '{matching_utt}' | "
                    f"Associated intent: '{intent_string}' | "
                    f"match score: {score} | ")

        return self.format_output(intent_string)
