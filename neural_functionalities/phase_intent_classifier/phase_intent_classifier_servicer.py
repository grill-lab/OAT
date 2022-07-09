from phase_intent_classifier_pb2_grpc import (
    PhaseIntentClassifierServicer,
    add_PhaseIntentClassifierServicer_to_server,
)

from . import DefaultPhaseIntentClassifier
from phase_intent_classifier_pb2 import (IntentRequest, IntentClassification, QuestionClassificationRequest,
                                         QuestionClassificationResponse, ScoreSentencesRequest, ScoreSentencesResponse)

from . import DefaultPhaseIntentClassifier


class Servicer(PhaseIntentClassifierServicer):
    
    def __init__(self):
        self.phase_intent_classifier = DefaultPhaseIntentClassifier()

    def classify_intent(self, intent_request: IntentRequest, context
    ) -> IntentClassification:
        return self.phase_intent_classifier.classify_intent(intent_request)

    def classify_question(self, request: QuestionClassificationRequest, context) -> QuestionClassificationResponse:
        return self.phase_intent_classifier.classify_question(request)

    def score_sentences(self, request: ScoreSentencesRequest, context) -> ScoreSentencesResponse:
        return self.phase_intent_classifier.score_sentences(request)