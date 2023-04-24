from phase_intent_classifier_pb2_grpc import (
    PhaseIntentClassifierServicer,
    add_PhaseIntentClassifierServicer_to_server,
)

from . import DefaultPhaseIntentClassifier
from phase_intent_classifier_pb2 import (IntentRequest, IntentClassification, QuestionClassificationRequest,
                                         QuestionClassificationResponse, ScoreSentencesRequest, ScoreSentencesResponse)

from . import DefaultPhaseIntentClassifier
from .similarity_classifier import SimilarityClassifier, NoMatchException
from .bert_intent_classifier import BERTIntentClassifier


class Servicer(PhaseIntentClassifierServicer):
    
    def __init__(self):
        self.similarity_classifier = SimilarityClassifier()
        self.bert_classifier = BERTIntentClassifier()
        # self.phase_intent_classifier = DefaultPhaseIntentClassifier()

    def classify_intent(self, intent_request: IntentRequest, context
    ) -> IntentClassification:
        try:
            # As Default, we try to use the similarity classifier
            return self.similarity_classifier.classify_intent(intent_request)
        except NoMatchException:
            # If No match for the similarity classifier, we use BERT instead
            # (This could be a configurable component)
            return self.bert_classifier.classify_intent(intent_request)

    # ? Do we need this method?
    def classify_question(self, request: QuestionClassificationRequest, context) -> QuestionClassificationResponse:
        return self.phase_intent_classifier.classify_question(request)

    # ? Do we need this method?
    def score_sentences(self, request: ScoreSentencesRequest, context) -> ScoreSentencesResponse:
        return self.phase_intent_classifier.score_sentences(request)