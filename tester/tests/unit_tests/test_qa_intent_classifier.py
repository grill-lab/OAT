import os
import json
import grpc

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import QuestionClassificationRequest

from utils import logger


def test_qa_intent_classifier():

    channel = grpc.insecure_channel(os.environ['NEURAL_FUNCTIONALITIES_URL'])
    phase_intent_classifier = PhaseIntentClassifierStub(channel)

    def create_query(utterance):
        qa_classification_request: QuestionClassificationRequest = QuestionClassificationRequest()
        qa_classification_request.utterance = utterance
        return qa_classification_request

    questions = [['How can I substitute milk?', 'ingredient substitution'],
                       ['What shall I do with the onions?','current task question'],
                       ['How much milk do I need?','ingredient question'],
                       ['How many steps are there?', "step question"],
                       ['At what temperature is water boiling', "general cooking or DIY question"],
                       ['How are you feeling today?', "chit chat"],
                       ['Can you share some images for this?', "system capabilities question"]]

    questions = []
    with open('/shared/test_data/test_qa.jsonl', 'r') as json_file:
        for line in json_file:
            questions.append(json.loads(line))
            
    logger.info("QA Intent Classifier Test")
    
    with open('/shared/test_reports/qa_intent_classifier.txt', 'a') as res_file:
        for question in questions:
            # request = create_query(question[0])
            request = create_query(question['Question'])
            question_type = phase_intent_classifier.classify_question(request).classification
            # logger.info(f"Utterance: {question[0]}     Classification: {question_type}      Class: {question[1]}")
            res_file.write(f"Utterance: {question['Question']}     Classification: {question_type}      Class: {question['Label']}\n")
