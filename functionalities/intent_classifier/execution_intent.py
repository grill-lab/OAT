from taskmap_pb2 import Session, InputInteraction
from intent_classifier_pb2 import NavigationIntent
from utils import logger


class IntentClassifier:

    @staticmethod
    def classify_intent(session: Session) -> NavigationIntent:
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction
        input_text = user_interaction.text

        navigation_intent = NavigationIntent()

        if len(user_interaction.intents) == 0:

            if "previous" in input_text.lower():
                label = "PreviousIntent"
            elif "repeat" in input_text.lower():
                label = "RepeatIntent"
            else:
                label = "NextIntent"

            logger.info(f'Classifying execution intent "{input_text}" as: {label}')
            navigation_intent.navigation_intent = label

        else:
            logger.info(f'Intent already provided for "{input_text}" as: {user_interaction.intents}')

        return navigation_intent
