import os
import grpc
from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import IntentRequest


class IntentParser(AbstractParser):

    def __init__(self):
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)

    def __call__(self, session: Session) -> Session:

        intent_request = IntentRequest()
        intent_request.utterance = session.turn[-1].user_request.interaction.text
        intent_request.request_attributes.phase = "planning"

        if (
            len(session.task_selection.candidates) > 0
            and len(session.task_selection.elicitation_utterances) > 0
            and session.task.taskmap.taskmap_id == ""
            or session.task_selection.preferences_elicited
        ):

            intent_request.request_attributes.options.extend(session.task_selection.candidates)

        intent_classification = self.phase_intent_classifier.classify_intent(intent_request)

        translation_dict = {
            "select": "SelectIntent",
            "cancel": "CancelIntent",
            "restart": "CancelIntent",
            "search": "SearchIntent",
            "yes": "YesIntent",
            "no": "NoIntent",
            "confused": "ConfusedIntent",
            "more_results": "MoreResultsIntent",
            "next": "NextIntent",
            "previous": "PreviousIntent",
            "stop_task": "StopIntent"
        }

        # check if model ouput is in translation dict before updating session
        intent_translation = translation_dict.get(intent_classification.classification)
        if intent_translation:
            session.turn[-1].user_request.interaction.intents.append(
                intent_translation
            )
        else:
            session.turn[-1].user_request.interaction.intents.append(
                "NotUnderstandIntent"
            )

        return session
