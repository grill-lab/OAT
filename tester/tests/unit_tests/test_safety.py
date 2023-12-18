import os

import grpc

from safety_pb2_grpc import SafetyStub
from safety_pb2 import SafetyUtterance


def test_suicide_prevention_check():
    channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
    safety_service = SafetyStub(channel)

    utterances = ['I feel lonely.', 'I hate myself.']
    for utterance in utterances:
        utterance_request = SafetyUtterance()
        utterance_request.text = utterance
        suicide_prevention_assessment = safety_service.suicide_prevention_check(utterance_request)
        print(f'Suicide preventation assessment for "{utterance}" is {suicide_prevention_assessment.is_safe}.')


def test_sensitivity_check():
    channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
    safety_service = SafetyStub(channel)

    utterances = ['I got fired yesterday.', 'Hey, are you religious?']
    for utterance in utterances:
        utterance_request = SafetyUtterance()
        utterance_request.text = utterance
        sensitivity_assessment = safety_service.sensitivity_check(utterance_request)
        print(f'Sensitivity assessment for "{utterance}" is {sensitivity_assessment.is_safe}.')


def test_offensive_speech_check():
    channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
    safety_service = SafetyStub(channel)

    utterances = ['I hate vanilla ice cream.', 'This recipe is crap.']
    for utterance in utterances:
        utterance_request = SafetyUtterance()
        utterance_request.text = utterance
        offensive_speech_assessment = safety_service.offensive_speech_check(utterance_request)
        print(f'Offensive speech assessment for "{utterance}" is {offensive_speech_assessment.is_safe}.')


def test_privacy_check():
    channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
    safety_service = SafetyStub(channel)

    utterances = ['My debit card number is 958302912902.', 'I have a question about my savings account.']
    for utterance in utterances:
        utterance_request = SafetyUtterance()
        utterance_request.text = utterance
        privacy_assessment = safety_service.privacy_check(utterance_request)
        print(f'Privacy assessment for "{utterance}" is {privacy_assessment.is_safe}.')
