# import os

# import grpc

# from taskmap_pb2 import Session
# from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
# from phase_intent_classifier_pb2 import IntentRequest

# from utils import logger


# def test_neural_parser():
#     channel = grpc.insecure_channel(os.environ['NEURAL_FUNCTIONALITIES_URL'])
#     intent_classifier = PhaseIntentClassifierStub(channel)

#     def create_request(utterance, turns) -> IntentRequest:
#         request: IntentRequest = IntentRequest()
#         request.utterance = utterance
#         request.turns.append(turns)
#         return request

#     dummy_requests = [
#         ("Why not"),
#         ("I'm done with this step"),
#         ("How do I fix my broken zipper?"),
#     ]

#     translation_dict = {
#                 "select": "SelectIntent",
#                 "cancel": "CancelIntent",
#                 "restart": "CancelIntent",
#                 "search": "SearchIntent",
#                 "yes": "YesIntent",
#                 "no": "NoIntent",
#                 "repeat": "RepeatIntent",
#                 "confused": "ConfusedIntent",
#                 "show_more_results": "MoreResultsIntent",
#                 "show_requirements": "ShowRequirementsIntent",
#                 "show_more_details": "ConfusedIntent",
#                 "next": "NextIntent",
#                 "previous": "PreviousIntent",
#                 "stop": "StopIntent",
#                 "chit_chat": "ChitChatIntent",
#                 "ASR_error": "ASRErrorIntent",
#                 "answer_question": "QuestionIntent",
#                 "inform_capabilities": "ConfusedIntent",
#                 "step_select": "ASRErrorIntent",
#                 "pause": 'PauseIntent',
#                 "start_task": 'StartTaskIntent',
#                 "set_timer": "createTimerIntent",
#                 "stop_timer": "deleteTimerIntent",
#                 "pause_timer": "pauseTimerIntent",
#                 "resume_timer": "resumeTimerIntent",
#                 "show_timers": "showTimerIntent",
#             }

#     session: Session = Session()
#     for utterance in dummy_requests:
#         new_turn = session.turn.add()
#         new_turn.user_request.interaction.text = utterance
#         request = create_request(utterance=new_turn.user_request.interaction.text, turns=new_turn)
#         intent_classification = intent_classifier.classify_intent(request)
#         intent_translation = translation_dict.get(intent_classification.classification)
#         if intent_translation:
#             logger.info(f"Intent classification for intent request \"{utterance}\" is: {intent_translation}.")
#         else:
#             logger.info("Could not classify.")
