from intent_classifier_pb2_grpc import IntentClassifierServicer, add_IntentClassifierServicer_to_server
from taskmap_pb2 import Session, InputInteraction

from intent_classifier_pb2 import DomainClassification, NavigationIntent, QuestionIntentCheck

from . import DefaultExecutionIntentClassifier
from . import DefaultDomainIntentClassifier
from . import DefaultQuestionIntentClassifier


class Servicer(IntentClassifierServicer):

    def __init__(self):
        self.execution_classifier = DefaultExecutionIntentClassifier()
        self.domain_classifier = DefaultDomainIntentClassifier()
        self.question_intent_classifier = DefaultQuestionIntentClassifier()

    def classify_intent(self, session: Session, context) -> NavigationIntent:
        return self.execution_classifier.classify_intent(session)

    def classify_domain(self, session: Session, context) -> DomainClassification:
        return self.domain_classifier.classify_intent(session)

    def check_question_intent(self, session, context) -> QuestionIntentCheck:
        return self.question_intent_classifier.classify_intent(session)