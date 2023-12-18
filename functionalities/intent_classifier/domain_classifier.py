from taskmap_pb2 import Session
from intent_classifier_pb2 import DomainClassification
from models.domain_classification import DomainClassifier as ClassifierModel
from utils import logger, Downloader


class DomainClassifier:

    def __init__(self):
        logger.info('Initialising domain classification!')
        artefact_id = "domain_classifier"
        downloader = Downloader()
        downloader.download([artefact_id])
        self.classifier = ClassifierModel()
        self.classifier.load(downloader.get_artefact_path(artefact_id))

    def classify_intent(self, session: Session) -> DomainClassification:
        utterance = session.turn[-1].user_request.interaction.text

        if 'covid' in utterance.lower():
            domain, confidence = 'MedicalDomain', 'high'

        else:
            domain, confidence = self.classifier.get_action(utterance)
 
        logger.info(f'DOMAIN CLASSIFICATION for {utterance} is classified as {domain} with {confidence} confidence')

        response = DomainClassification()
        response.domain = domain
        response.confidence = confidence

        return response
