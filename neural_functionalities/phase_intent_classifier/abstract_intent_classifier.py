from abc import ABC, abstractmethod
from typing import Union, Dict

from phase_intent_classifier_pb2 import (IntentRequest, IntentClassification)

class AbstractClassifier(ABC):

    def preprocess_request(self, intent_request: IntentRequest) -> Dict[str, str]:

        user_utter = intent_request.turns[-1].user_request.interaction.text
        if len(intent_request.turns) == 1:
            system_utter = 'Hi, this is an Alexa Prize TaskBot. I know about cooking, ' \
                           'home improvement, and arts & crafts. What can I help you with?'
        else:
            system_utter = intent_request.turns[-2].agent_response.interaction.speech_text

        return {
            'system': system_utter,
            'user': user_utter
        }

    def format_output(self, string_function) -> IntentClassification:
        output = IntentClassification()

        pred_function = string_function.split('(')[0]
        output.classification = pred_function
        output.attributes.raw = string_function

        try:
            if pred_function == "select":
                # default to 0 if there are no options
                output.attributes.option = int(string_function.split("(")[-1].split(")")[0])

            if pred_function == "step_select":
                # default to 0
                output.attributes.step = int(string_function.split("(")[-1].split(")")[0])
        except:
            output.classification = 'next'

        return output

    @abstractmethod
    def classify_intent(
            self, intent_request: IntentRequest
    ) -> IntentClassification:
        """
        Takes in the current utterance and outputs an intent classification from a neural model.
        Classification depends on what phase the user is in the system, hence the multiple
        return types.
        """
        pass
