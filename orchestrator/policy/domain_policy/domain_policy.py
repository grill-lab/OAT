from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, OutputInteraction, Task, ScreenInteraction, Image, SessionState
from intent_classifier_pb2_grpc import IntentClassifierStub
from intent_classifier_pb2 import DomainClassification
from exceptions import PhaseChangeException
from dangerous_task_pb2_grpc import DangerousStub

import grpc
import os
import json
import random

from .rulebook import rulebook
from utils import close_session, is_in_user_interaction, consume_intents, DANGEROUS_TASK_RESPONSES, logger


class DomainPolicy(AbstractPolicy):

    def __init__(self):

        self.rulebook = rulebook
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.dangerous_task_filter = DangerousStub(channel)

    @staticmethod
    def __populate_screen(screen):

        screen.headline = "Hi, I'm TaskBot!"

        screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

        cooking_image_options = ['cooking-15', 'cooking-11', 'cooking-9', 'cooking-7', 'cooking-6', 'cooking-1']
        selected_cooking_image = random.choice(cooking_image_options)
        cooking_image: Image = screen.image_list.add()
        cooking_image.path = f'https://grill-bot-data.s3.amazonaws.com/images/{selected_cooking_image}.jpg'
        cooking_image.title = 'Cooking'
        cooking_image.description = '\"Creamy Zucchini Pasta\"'
        # cooking_image.response_on_click = 'cook a pizza'

        diy_image_options = ['diy-6', 'diy-7', 'diy-5', 'diy-4', 'diy-3', 'diy-2']
        selected_diy_image = random.choice(diy_image_options)
        diy_image: Image = screen.image_list.add()
        diy_image.path = f'https://grill-bot-data.s3.amazonaws.com/images/{selected_diy_image}.jpg'
        diy_image.title = 'Home Improvement'
        diy_image.description = '\"How to paint a wall\"'
        # diy_image.response_on_click = 'paint a wall'

        suggest_image: Image = screen.image_list.add()
        suggest_image.path = f'https://grill-bot-data.s3.amazonaws.com/images/surprise.jpg'
        suggest_image.title = 'Pick of the day'
        suggest_image.description = 'Choose our favourites'

        PROMPTS = ["help me cook", "the best pasta dish", "What is your favourite dish?"]
        screen.hint_text = random.sample(PROMPTS, 1)[0]
        theme_choices = ['rice', 'wood work', 'pasta']
        selected_theme = random.choice(theme_choices)
        screen.on_click_list.extend(['Creamy Zucchini Pasta', 'paint a wall', selected_theme])
        screen.background = 'https://grill-bot-data.s3.amazonaws.com/images/multi_domain_default.jpg'

        return screen

    def __get_rule(self, domain, confidence):
        for rule in self.rulebook:
            if rule['confidence'] == confidence and domain in rule['conditions']:
                return rule

    @staticmethod
    def __raise_phase_change(session, phase, domain):

        # reset error handling counter
        session.error_counter.no_match_counter = 0

        session.task.state.domain_interaction_counter = 0

        session.domain = domain
        session.task.phase = phase
        raise PhaseChangeException()

    def step(self, session: Session) -> (Session, OutputInteraction):

        output = OutputInteraction()

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["CancelIntent", "AMAZON.CancelIntent", 'StopIntent', 'AMAZON.StopIntent']):

            consume_intents(session.turn[-1].user_request.interaction,
                            intents_list=["CancelIntent", "AMAZON.CancelIntent"])
            session, output = close_session(session, output)
            return session, output

        dangerous_assessment = self.dangerous_task_filter.dangerous_query_check(session)
        if dangerous_assessment.is_dangerous:
            output = OutputInteraction()
            output.speech_text = random.choice(DANGEROUS_TASK_RESPONSES)
            session, output = close_session(session, output)
            return session, output

        steps = session.task.state.domain_interaction_counter

        # # Retrieve a set of candidates calling the searcher
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        intent_classifier = IntentClassifierStub(channel)

        domain_response: DomainClassification = intent_classifier.classify_domain(session)

        confidence = domain_response.confidence
        top_domain = domain_response.domain

        if steps > 2:
            # High Confidence
            rule = self.__get_rule(top_domain, "high")
        else:
            # High Confidence
            rule = self.__get_rule(top_domain, confidence)

        if '[REDIRECT]' in rule['response']:
            # Assign domain to session, change phase and raise Exception
            if top_domain == "CookingDomain":
                self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.COOKING)
            else:
                self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.DIY)

        output.speech_text = random.choice(rule['response'][session.error_counter.no_match_counter])

        # since we are not redirecting, we should increment the no match counter
        if session.error_counter.no_match_counter < 2:
            session.error_counter.no_match_counter += 1

        if not session.headless:
            self.__populate_screen(output.screen)
            if session.error_counter.no_match_counter > 0:
                user_utterance = session.turn[-1].user_request.interaction.text
                output.screen.headline = f'I understood: "{user_utterance}"'

        # The role of this counter is to determine the Absolute Threshold to use, if we have High classification
        # we don't want to change the confidence level required
        if confidence == 'low':
            session.task.state.domain_interaction_counter += 1

        return session, output
