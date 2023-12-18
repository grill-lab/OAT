import os
import json
import grpc
import random
import stream

from taskmap_pb2 import Session, OutputInteraction, TaskMap

from qa_pb2_grpc import QuestionAnsweringStub, TaskQuestionAnsweringStub
from qa_pb2 import QAQuery, QAResponse, QARequest

from typing import Tuple

from utils import logger, close_session, is_in_user_interaction

from intent_classifier_pb2_grpc import IntentClassifierStub
from intent_classifier_pb2 import DomainClassification

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import QuestionClassificationRequest, QuestionClassificationResponse

from dangerous_task_pb2_grpc import DangerousStub


def read_protobuf_list_from_file(path,  proto_message):
    return [d for d in stream.parse(path, proto_message)]

def _qa_system():
    task_maps = read_protobuf_list_from_file('/shared/test_data/finals_taskgraphs.bin', TaskMap)
    taskmaps_dict = {}
    for task in task_maps:
        taskmaps_dict[task.source_url] = task
    
    functionalities_channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
    neural_functionalities_channel = grpc.insecure_channel(os.environ['NEURAL_FUNCTIONALITIES_URL'])
    external_functionalities_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
    qa_systems = {
        "GENERAL_QA": QuestionAnsweringStub(neural_functionalities_channel),
        "TASKMAP_QA": TaskQuestionAnsweringStub(neural_functionalities_channel),
    }

    intent_classifier = IntentClassifierStub(functionalities_channel)
    dangerous_task_filter = DangerousStub(external_functionalities_channel)
    phase_intent_classifier = PhaseIntentClassifierStub(neural_functionalities_channel)
    
    questions = []
    with open('/shared/test_data/test_qa.jsonl', 'r') as json_file:
        for line in json_file:
            questions.append(json.loads(line))
    
    logger.info("QA System Test")
    
    with open('/shared/test_reports/qa_finals_test.txt', 'a') as res_file:
        for question in questions:
            qa_request: QARequest = QARequest()
            qa_request.query.text = question['Question']
            qa_request.query.taskmap.CopyFrom(taskmaps_dict[question['url']])
            
            qa_classification_request: QuestionClassificationRequest = QuestionClassificationRequest()
            qa_classification_request.utterance = question['Question']
            question_type = phase_intent_classifier.classify_question(qa_classification_request).classification
        
            if question_type in ["ingredient question", "current task question", "step question", "ingredient substitution"]:
                answer = qa_systems['TASKMAP_QA'].synth_response(qa_request).SerializeToString()
            else:
                answer = qa_systems['GENERAL_QA'].synth_response(qa_request).SerializeToString()
                
            res_file.write(f"Question: {question['Question']}   Answer (true): {question['Answer']}  Answer (generated): {answer}\n")
