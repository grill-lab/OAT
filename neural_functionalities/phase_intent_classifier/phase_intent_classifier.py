from .abstract_intent_classifier import AbstractClassifier
from phase_intent_classifier_pb2 import (
    IntentRequest,
    IntentClassification,
    QuestionClassificationRequest,
    QuestionClassificationResponse,
    ScoreSentencesRequest,
    ScoreSentencesResponse
)

from models.RinD.model_utils import ModelFormatter, UnifiedQA_intent_prediction
from models.RinD.models import Reasoning_in_Decoder
from models.question_classifier.question_classifier_model import TextClassifier
from transformers import set_seed, AutoTokenizer, AutoModelForSeq2SeqLM, pipeline, AdamW

from dotmap import DotMap
import grpc
from sentence_transformers import SentenceTransformer, util
import ujson as json
import os

import torch
from utils import logger, indri_stop_words, jaccard_similarity
import jsonlines

def load_annotations():
    try:
        annotations = list(jsonlines.Reader(open('/shared/file_system/logs/LIVE_intent_annotations.jsonl', 'r')).iter())
        logger.info("loaded existing annotations")
    except Exception as e:
        annotations = []
        logger.info('creating empty annotations')
        save_annotations(annotations)
    return annotations

def add_new_annotation(new_annot):
    annotations = load_annotations()
    past_length = len(annotations)
    annotations = [annot for annot in annotations if not (new_annot['user'] == annot['user'] and new_annot['system'] == annot['system'])]
    if past_length != len(annotations):
        logger.info("Overwriting existing annotation")
    annotations.append(new_annot)
    save_annotations(annotations)

def save_annotations(annotations):
    jsonlines.Writer(open('/shared/file_system/logs/LIVE_intent_annotations.jsonl', 'w')).write_all(annotations)


class PhaseIntentClassifier(AbstractClassifier):
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

        logger.info('loading RinD intent classifier')
        model_location = '/shared/file_system/models/policy_classification/UQA_intent_model_1185'
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_location)
        self.model.eval()
        tokenizer = AutoTokenizer.from_pretrained("allenai/unifiedqa-t5-base")
        self.model.tokenizer = tokenizer

        logger.info('loading question type classifier')
        self.question_classifier = TextClassifier.from_pretrained('/shared/file_system/models/question_type_classifier')

        if torch.cuda.is_available():
            self.model.to('cuda')
            self.question_classifier.to('cuda')

        logger.info(f"Loaded RinD UnifiedQA intent parsing model from: {model_location}")

    def pre_classify_intent(self, utter, threshold=0.85):
        utter_emb = self.embedder.encode(utter, convert_to_tensor=True)
        similarity_scores = util.cos_sim(utter_emb, self.utterance_embeddings)[0]
        sorted_indexes = similarity_scores.argsort(descending=True)
        sorted_scores = similarity_scores[sorted_indexes]
        passes_threshold = True if sorted_scores[0] > threshold else False

        return self.utterances[sorted_indexes[0]], self.intents_map[sorted_indexes[0]], sorted_scores[0], passes_threshold

    def classify_intent(
        self, intent_request: IntentRequest
    ) -> IntentClassification:

        user_utter = intent_request.turns[-1].user_request.interaction.text
        clossest_utter, intent, score, single_utter_above_thresh = self.pre_classify_intent(user_utter)
        logger.info(f"Single utterance intent classification:")
        logger.info(f"Clossest utterance: '{clossest_utter}' | Associated intent: '{intent}' | "
                    f"match score: {score} | score above threshold: '{single_utter_above_thresh}' | ")

        intent_classification = IntentClassification()

        if len(intent_request.turns) == 1:
            system_utter = 'Hi, this is an Alexa Prize TaskBot. I know about cooking, ' \
                           'home improvement, and arts & crafts. What can I help you with?'
        else:
            system_utter = intent_request.turns[-2].agent_response.interaction.speech_text

        sample = {'system': system_utter, 'user': user_utter}
        if ">>>" in user_utter:
            prediction_string = user_utter.split(">>>")[-1].strip()
            logger.info(f"Overriding RinD intent to ->'{prediction_string}")
            sample['annotation'] = prediction_string
            sample['user'] = intent_request.turns[-2].user_request.interaction.text
            if len(intent_request.turns) >=3:
                sample['system'] = intent_request.turns[-3].agent_response.interaction.speech_text
            add_new_annotation(sample)
        elif single_utter_above_thresh:
            logger.info(f"Skipping Full RinD since good single intent match")
            prediction_string = intent
        else:
            samples = UnifiedQA_intent_prediction([sample], self.model)
            prediction_string = samples[0]['intent_pred']

            logger.info('######## RinD model input #########')
            logger.info(samples[0]['model_input'])
            logger.info('######## RinD prediction ##########')
            logger.info(prediction_string)
            logger.info('###################################')

        pred_function = prediction_string.split('(')[0]
        intent_classification.classification = pred_function
        intent_classification.attributes.raw = prediction_string

        try:
            if pred_function == "select":
                # default to 0 if there are no options
                intent_classification.attributes.option = int(prediction_string.split("(")[-1].split(")")[0])

            if pred_function == "step_select":
                # default to 0
                intent_classification.attributes.step = int(prediction_string.split("(")[-1].split(")")[0])
        except:
            intent_classification.classification = 'next'

        return intent_classification

    def classify_question(self, request: QuestionClassificationRequest) -> QuestionClassificationResponse:
        resp = QuestionClassificationResponse()
        resp.classification = self.question_classifier.predict([request.utterance])[0]
        return resp

    def score_sentences(self, request: ScoreSentencesRequest) -> ScoreSentencesResponse:
        list_embeddings = self.embedder.encode(request.sentences, convert_to_tensor=True)
        query_embedding = self.embedder.encode(request.query, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, list_embeddings)[0]
        sorted_idxs = cos_scores.argsort(descending=True)
        response = ScoreSentencesResponse()
        response.sorted_idxs.extend(sorted_idxs.tolist())
        response.sorted_scores.extend(cos_scores[sorted_idxs].tolist())
        return response