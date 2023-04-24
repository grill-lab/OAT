from .abstract_intent_classifier import AbstractClassifier
import torch
from utils import logger
from string import Template
from phase_intent_classifier_pb2 import (
    IntentRequest,
    IntentClassification,
)
from transformers import BertTokenizer, BertForSequenceClassification


class BERTIntentClassifier(AbstractClassifier):
    def __init__(self):
        logger.info('Loading Intent Classification Model')

        PATH = "/shared/file_system/models/neural_decision_classifier.pt"
        self.model = torch.load(PATH, map_location="cpu")
        self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        self.model.eval()

        logger.info('Intent Classification model complete!')

        if torch.cuda.is_available():
            self.model.to('cuda')

    def classify_intent(
            self, intent_request: IntentRequest
    ) -> IntentClassification:
        sample = self.preprocess_request(intent_request)
        template = Template("Bot: $system\nUser: $user")

        input_samples = [template.substitute(sample)]
        inputs = self.tokenizer(input_samples,
                                return_tensors="pt",
                                ).to(self.model.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits

        predicted_class_id = logits.argmax().item()
        function_string = self.model.config.id2label[predicted_class_id]

        logger.info(f"Bert classified utterance: {sample['user']} "
                    f"with intent: {function_string}")

        return self.format_output(function_string)

    # def classify_question(self, request: QuestionClassificationRequest) -> QuestionClassificationResponse:
    #     pass
    #
    # def score_sentences(self, request: ScoreSentencesRequest) -> ScoreSentencesResponse:
    #     pass
