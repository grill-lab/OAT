import os
import random
from typing import Dict, Tuple, Union

import grpc

from dangerous_task_pb2_grpc import DangerousStub
from exceptions import PhaseChangeException
from intent_classifier_pb2 import DomainClassification
from intent_classifier_pb2_grpc import IntentClassifierStub
from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Image, OutputInteraction, ScreenInteraction, Session, Task
from utils import (
    DANGEROUS_TASK_RESPONSES, close_session, consume_intents, is_in_user_interaction, set_source,
    repeat_screen_response, logger, INTRO_PROMPTS, build_chat_screen, should_trigger_theme, PAUSING_PROMPTS,
    JOKE_TRIGGER_WORDS
)
from theme_pb2 import ThemeResults
from phase_intent_classifier_pb2 import IntentRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from semantic_searcher_pb2 import SemanticQuery, ThemeMapping, ThemeDocument
from semantic_searcher_pb2_grpc import SemanticSearcherStub

from .rulebook import rulebook
from .theme_suggestion import ThemeSuggestion
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from policy.chitchat_policy import DefaultPolicy as DefaultChitChatPolicy

from .hand_crafted_home_screen import HandCraftedHome


class DomainPolicy(AbstractPolicy):
    FALLBACK_THEMES = ['Italian', 'Desserts', 'Healthy food']

    def __init__(self):

        self.rulebook = rulebook
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        self.dangerous_task_filter = DangerousStub(external_channel)
        self.theme_suggester = ThemeSuggestion()
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.domain_classifier = IntentClassifierStub(channel)
        self.search_again = False
        self.chitchat_policy = DefaultChitChatPolicy()
        self.qa_policy = DefaultQAPolicy()
        self.hand_crafter = HandCraftedHome()
        self.semantic_searcher = SemanticSearcherStub(neural_channel)

    def __get_theme(self, user_utterance: str) -> bool:
        semantic_query: SemanticQuery = SemanticQuery()
        semantic_query.text = user_utterance
        matched_theme: ThemeMapping = self.semantic_searcher.search_theme(semantic_query)
        return matched_theme.theme

    def __populate_screen(self, screen: ScreenInteraction, current_theme: ThemeResults) -> ScreenInteraction:
        """Populate a ScreenInteraction with default choices when domain is not recognised.

        If the domain classifier makes a Cooking/DIY classification, it will raise a 
        PhaseChangeException to switch to the PlanningPolicy. If the domain is not recognised,
        the policy returns a response which informs the user what the bot can handle. If the
        session is on a non-headless device, this method is used to populate the screen 
        content in the response. 

        Args:
            screen (ScreenInteraction): the ScreenInteraction from the current OutputInteraction

        Returns:
            updated ScreenInteraction
        """

        screen.headline = "Hi, I'm TaskBot!"

        screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

        cooking_image_options = ['cooking-15', 'cooking-11', 'cooking-9', 'cooking-7', 'cooking-6', 'cooking-1']
        selected_cooking_image = random.choice(cooking_image_options)
        cooking_image: Image = screen.image_list.add()
        cooking_image.path = f'https://oat-2-data.s3.amazonaws.com/images/{selected_cooking_image}.jpg'
        cooking_image.title = 'Cooking'
        cooking_image.description = '\"Creamy Zucchini Pasta\"'
        # cooking_image.response_on_click = 'cook a pizza'

        diy_image_options = ['diy-6', 'diy-7', 'diy-5', 'diy-4', 'diy-3', 'diy-2']
        selected_diy_image = random.choice(diy_image_options)
        diy_image: Image = screen.image_list.add()
        diy_image.path = f'https://oat-2-data.s3.amazonaws.com/images/{selected_diy_image}.jpg'
        diy_image.title = 'Home Improvement'
        diy_image.description = '\"How to paint a wall\"'
        # diy_image.response_on_click = 'paint a wall'

        suggest_image: Image = screen.image_list.add()

        selected_theme = self.theme_suggester.get_theme_title(current_theme)

        if selected_theme == "":
            # theme_choices = self.FALLBACK_THEMES
            # selected_theme = random.choice(theme_choices)
            selected_theme = "Joke of the day"
            suggest_image.path = f'https://oat-2-data.s3.amazonaws.com/images/surprise.jpg'
            suggest_image.description = "Can a robot be funny?"
        else:
            if len(current_theme.results.candidates) > 0:
                suggest_image.path = current_theme.results.candidates[0].thumbnail_url
            elif current_theme.thumbnail != "":
                suggest_image.path = current_theme.thumbnail
            else:
                suggest_image.path = f'https://oat-2-data.s3.amazonaws.com/images/surprise.jpg'

            sub_caption = self.theme_suggester.get_subcaption(current_theme)
            suggest_image.description = sub_caption

        PROMPTS = [selected_theme, "what can you do"]

        suggest_image.title = selected_theme

        screen.hint_text = random.sample(PROMPTS, 1)[0]
        screen.on_click_list.extend(['cooking', 'home improvement', "tell me a joke"])

        return screen

    def __get_rule(self, domain: str, confidence: str) -> Union[str, Dict, None]:
        """Get a response from the rulebook given a domain and confidence level.

        The domain classifier returns a string representing the domain and another string
        giving the confidence level of the classification (high/low). This method performs 
        a lookup in the ``rulebook`` dict defined in ``domain_policy.rulebook`` to obtain
        a dict containing the appropriate response. 

        The results of the lookup are variable. For example, a "high" confidence classification
        of Cooking/DIY returns a string indicating things should be redirected to the 
        PlanningPolicy. In other cases, the response is a dict which defines different levels
        of fallback responses to cope with repeated classification failures. 

        Args:
            domain (str): the classified domain (e.g. "DIYDomain", "CookingDomain")
            confidence (str): classification confidence (e.g. "high", "low")

        Returns:
            either a string or a dict, depending on the inputs
        """
        for rule in self.rulebook:
            if rule['confidence'] == confidence and domain in rule['conditions']:
                return rule

    @staticmethod
    def __raise_phase_change(session: Session, phase: Task.TaskPhase.ValueType,
                             domain: Session.Domain.ValueType) -> None:
        """Redirect control of the response to a different policy.

        This method is called in the event of a successful classification of Cooking or DIY. 
        It will set the ``session.domain`` and `Session.task.phase``` fields to trigger the
        PlanningPolicy when control returns to PhasedPolicy, and then raise a PhaseChangeException
        to jump back to ``PhasedPolicy.__route_policy``. 

        Args:
            session (Session): the current Session object
            phase (Task.TaskPhase.ValueType): a value from the Task.TaskPhase enum
            domain (Session.Domain.ValueType): a value from the Session.Domain enum

        Returns:
            Nothing, always raises a PhaseChangeException
        """

        # reset error handling counter
        session.error_counter.no_match_counter = 0

        session.task.state.domain_interaction_counter = 0

        session.domain = domain
        session.task.phase = phase
        raise PhaseChangeException()

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the DomainPolicy class.

        This method is responsible for making a domain classification from the current session,
        then either redirecting to the PlanningPolicy (if successful) by raising a 
        PhaseChangeException, or providing a fallback/error response (if not successful or 
        a non-allowed domain is detected).

        It will also check for CancelIntent/StopIntents and end the session if found, and run the
        dangerous task filter before proceeding to classification. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction), or raises PhaseChangeException
        """
        output = OutputInteraction()

        # don't need to classify intents if we are in the help corner
        if session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:
            if "_button" in session.turn[-1].user_request.interaction.text \
                    and not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')
            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.append("InformIntent")
            raise PhaseChangeException()

        current_theme = self.theme_suggester.get_current_theme()
        if current_theme.theme_word != "":
            logger.info(current_theme.theme_word)
            logger.info(current_theme.description)
            logger.info(current_theme.hand_curated)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["CancelIntent", 'StopIntent']):
            consume_intents(session.turn[-1].user_request.interaction,
                            intents_list=["CancelIntent"])
            session.task.phase = Task.TaskPhase.CLOSING
            raise PhaseChangeException()

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  utterances_list=["search", "search again"]) \
                or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=['Consumed.CancelIntent']):
            output.speech_text = "I can help you cook and do some cool home projects! " \
                                 "Let's get started, what do you want to do?"

            self.__populate_screen(output.screen, current_theme=current_theme)
            session.greetings = True
            self.search_again = True

            set_source(output)
            return session, output

        dangerous_assessment = self.dangerous_task_filter.dangerous_query_check(session)
        if dangerous_assessment.is_dangerous:
            output = OutputInteraction()
            output.speech_text = random.choice(DANGEROUS_TASK_RESPONSES)
            session, output = close_session(session, output)
            set_source(output)
            return session, output

        if session.task_selection.theme.theme != "":
            trigger_theme, _ = should_trigger_theme(user_utterance=session.turn[-1].user_request.interaction.text,
                                                    theme_word=session.task_selection.theme.theme)
            if current_theme.hand_curated and trigger_theme:
                logger.info('We have triggered our custom home screen! ')
                screen: ScreenInteraction = ScreenInteraction()
                if current_theme.description == "":
                    logger.info(current_theme)
                    logger.info(f'Something went wrong so the theme is now {session.task_selection.theme.theme}')
                    current_theme.description = session.task_selection.theme.theme

                output = self.hand_crafter.populate_custom_screen(screen=screen, current_theme=current_theme)

                session.task_selection.theme.Clear()
                set_source(output)
                return session, output

        steps = session.task.state.domain_interaction_counter
        classify_intent = True

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  utterances_list=['hi', 'hello']):
            logger.info(
                f"Skipping intent classification domain due to {session.turn[-1].user_request.interaction.text}")
            classify_intent = False

        elif len(session.turn[-1].user_request.interaction.intents) > 0:
            logger.info('Since we rerouted, no need for intent classification')
            classify_intent = False

        if classify_intent:
            intent_request = IntentRequest()
            intent_request.utterance = session.turn[-1].user_request.interaction.text
            for turn in session.turn:
                intent_request.turns.append(turn)

            intent_classification = self.phase_intent_classifier.classify_intent(intent_request)
            session.turn[-1].user_request.interaction.params.append(intent_classification.attributes.raw)
            translation_dict = {"yes": "YesIntent", "stop": "StopIntent", "answer_question": "QuestionIntent",
                                "chit_chat": "ChitChatIntent", "confused": "ConfusedIntent",
                                "select": "SelectIntent", "inform_capabilities": "InformIntent", "pause": "PauseIntent"}

            # check if model output is in translation dict before updating session
            intent_translation = translation_dict.get(intent_classification.classification)
            if intent_translation:
                session.turn[-1].user_request.interaction.intents.append(
                    intent_translation
                )
                logger.info(f"Intent classification in domain: {intent_translation}")
            else:
                logger.info(f"Intent classification: {intent_classification.classification} not handled in domain, "
                            f"handled by fallback. ")

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['StopIntent']):
            session.task.phase = Task.TaskPhase.CLOSING
            session.task.state.requirements_displayed = False
            session.task.state.validation_page = 0
            session.task.taskmap.Clear()
            raise PhaseChangeException()

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['PauseIntent']):
            output = OutputInteraction()
            output.idle_timeout = 1800
            output.pause_interaction = True
            if session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True
                output.speech_text = random.sample(PAUSING_PROMPTS, 1)[0]
            else:
                output.speech_text = random.sample(PAUSING_PROMPTS, 1)[0]

            output: OutputInteraction = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["InformIntent", "ConfusedIntent"]):
            # this will bounce things back to PhasedPolicy, where the next call to
            # __route_policy will trigger the IntentsPolicy with one of the above intents
            raise PhaseChangeException()

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['QuestionIntent', 'ChitChatIntent']):
            trigger_theme = False

            if not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          utterances_list=JOKE_TRIGGER_WORDS):
                theme_title = ""
                last_utterance = session.turn[-1].user_request.interaction.text

                # we have a theme, but it's a v2 theme
                if not current_theme.hand_curated:
                    theme_title = self.theme_suggester.get_theme_title(current_theme)
                    trigger_theme, _ = should_trigger_theme(user_utterance=last_utterance, theme_word=theme_title)

                # we have no current theme
                elif current_theme.theme_word != "":
                    for theme in self.FALLBACK_THEMES:
                        trigger_theme, theme_title = should_trigger_theme(user_utterance=last_utterance,
                                                                          theme_word=theme)
                        if trigger_theme:
                            theme_title = theme
                            break

                # we have a v3 theme
                else:
                    user_utterance = session.turn[-1].user_request.interaction.text
                    for theme in current_theme.popular_tasks:
                        trigger_theme, _ = should_trigger_theme(theme_word=theme, user_utterance=user_utterance)
                        if trigger_theme:
                            theme_title = theme
                            break
                        else:
                            trigger_theme, _ = should_trigger_theme(user_utterance,
                                                                    self.theme_suggester.get_theme_title(current_theme))
                            if trigger_theme:
                                theme_title = self.theme_suggester.get_theme_title(current_theme)

                if not trigger_theme:

                    # check if QA/ chitchat is within domain before answering

                    domain_response: DomainClassification = self.domain_classifier.classify_domain(session)
                    confidence = domain_response.confidence
                    top_domain = domain_response.domain

                    logger.info(f"Classified DOMAIN: {top_domain}")

                    if top_domain in ["MedicalDomain", "FinancialDomain",
                                      "LegalDomain"] and domain_response.confidence == "high":

                        logger.info('QA outwith domain - responding with default responses')
                        rule = self.__get_rule(top_domain, confidence)
                        output.speech_text = random.choice(rule['response'][session.error_counter.no_match_counter])

                        # since we are not redirecting, we should increment the no match counter
                        if session.error_counter.no_match_counter < 2:
                            session.error_counter.no_match_counter += 1

                        if not session.headless:
                            self.__populate_screen(output.screen, current_theme)
                            if session.error_counter.no_match_counter > 0:
                                user_utterance = session.turn[-1].user_request.interaction.text
                                output.screen.headline = f'I understood: "{user_utterance}"'

                        # The role of this counter is to determine the Absolute Threshold to use, if we have High
                        # classification we don't want to change the confidence level required
                        if confidence == 'low':
                            session.task.state.domain_interaction_counter += 1

                        set_source(output)
                        return session, output
                else:

                    logger.info(f'Classified as QA or Chit Chat, but should actually be Theme Selection due to '
                                f'{last_utterance} similar to current theme: {theme_title}')

            # ---- all safe - answer QA/ chitchat below ----

            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=['QuestionIntent']) and not trigger_theme \
                    and not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                                   utterances_list=JOKE_TRIGGER_WORDS):
                _, output = self.qa_policy.step(
                    session
                )
                user_utterance = session.turn[-1].user_request.interaction.text
                output = build_chat_screen(policy_output=output, user_utterance=user_utterance, session=session)
                output.screen.headline = f'I understood: "{user_utterance}"'
                set_source(output)
                return session, output

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=['ChitChatIntent'],
                                        utterances_list=JOKE_TRIGGER_WORDS) and session.greetings and not trigger_theme:
                if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          utterances_list=['hi', 'hello']):
                    logger.info(f"Skipping chit chat in domain due to {session.turn[-1].user_request.interaction.text}")
                else:
                    session, output = self.chitchat_policy.step(session)
                    return session, output

        elif not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["SearchIntent"]) \
                and not self.search_again and current_theme.description != "":

            theme_title = self.theme_suggester.get_theme_title(current_theme) \
                if current_theme.hand_curated is False else session.task_selection.theme.theme

            user_utterance = session.turn[-1].user_request.interaction.text.lower()
            trigger_theme, _ = should_trigger_theme(user_utterance=user_utterance.lower(), theme_word=theme_title)
            if current_theme.hand_curated and trigger_theme:
                logger.info(f'We are populating the {theme_title} screen')
                theme: ThemeDocument = ThemeDocument()
                theme.theme = current_theme.theme_word
                session.task_selection.theme.MergeFrom(theme)
                raise PhaseChangeException()

            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      utterances_list=theme_title):
                session.turn[-1].user_request.interaction.intents.append('SearchIntent')
                session.task_selection.theme.theme = theme_title
                consume_intents(session.turn[-1].user_request.interaction, intents_list=["SelectIntent"])
                self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.COOKING)

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["SelectIntent"]):
                session.turn[-1].user_request.interaction.intents.append('SearchIntent')
                consume_intents(session.turn[-1].user_request.interaction, intents_list=["SelectIntent"])
                self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.COOKING)

        # if we have a theme, and we do not reroute to searching -> now we build the intro prompt
        if steps == 0 and current_theme.description != "" and \
                not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                           intents_list=["SearchIntent"]) and not self.search_again:
            # if we do not reroute from another phase, build theme intro prompt
            if not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=['PreviousIntent', 'NoIntent', 'MoreResultsIntent',
                                                        'NextIntent']):
                output.speech_text = self.theme_suggester.build_theme_intro_prompt(current_theme)
            else:
                # do not recommend theme again since we already said it earlier
                output.speech_text = random.choice(INTRO_PROMPTS)
                session.task_selection.theme.Clear()
            confidence = "low"

        else:
            # this is the "fallback": the user has heard the intro prompt already.
            # We either go to the rulebook or we go into search by rerouting to planner

            rule = {"response": ""}
            top_domain = ""
            confidence = "low"

            if not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=["ThemeSearchIntent"]):
                del session.turn[-1].user_request.interaction.intents[:]
                if len(session.turn) > 1:
                    del session.turn[-2].user_request.interaction.intents[:]

                trigger_theme = False
                theme_title = ""
                user_utterance = session.turn[-1].user_request.interaction.text

                if current_theme.theme_word != "":
                    if not current_theme.hand_curated:
                        theme_title = self.theme_suggester.get_theme_title(current_theme)
                        trigger_theme, _ = should_trigger_theme(user_utterance=user_utterance, theme_word=theme_title)
                    else:
                        trigger_theme, _ = should_trigger_theme(user_utterance,
                                                                self.theme_suggester.get_theme_title(current_theme))
                        if trigger_theme:
                            theme_title = self.theme_suggester.get_theme_title(current_theme)
                        else:
                            for theme in current_theme.popular_tasks:
                                trigger_theme, _ = should_trigger_theme(theme_word=theme, user_utterance=user_utterance)
                                if trigger_theme:
                                    theme_title = theme
                                    break

                        # super hacky, change later
                        if not trigger_theme:
                            checks = [word for word in user_utterance.split(' ') if word.lower() in ["national", "day"]]
                            if len(checks) > 0:
                                theme_title = user_utterance
                                trigger_theme = True
            else:
                # we have a ThemeSearchIntent in intents already, meaning we have routed back from theme policy
                # to not bounce forever, we keep the intents
                trigger_theme = False
                logger.info("Came from theme policy, keeping intents to avoid bouncing!")

            if trigger_theme:
                logger.info(f'Skipping domain classification due to theme triggered: {theme_title}')

                # evaluate whether we want to set the theme or not in session variable
                session.task_selection.theme.theme = theme_title

                if current_theme.hand_curated and trigger_theme \
                        and current_theme.description == session.task_selection.theme.theme:
                    logger.info(current_theme)
                    logger.info("we want to build the custom screen in domain, rerouting")
                    raise PhaseChangeException()

                if current_theme.hand_curated and not trigger_theme:
                    logger.info("hand curated theme")
                    for theme in current_theme.popular_tasks:
                        trigger_theme, _ = should_trigger_theme(theme_word=theme,
                                                                user_utterance=session.turn[
                                                                    -1].user_request.interaction.text)
                        if trigger_theme:
                            logger.info("theme triggered")
                            session.task_selection.theme.theme = theme
                            break
            else:
                # saying previous screen gets classified as DIYDomain by classifier
                if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          utterances_list=["previous screen"]):
                    confidence = "high"
                    top_domain = "UndefinedDomain"
                else:
                    domain_response: DomainClassification = self.domain_classifier.classify_domain(session)

                    confidence = domain_response.confidence
                    top_domain = domain_response.domain

                    if top_domain in ["MedicalDomain", "FinancialDomain", "LegalDomain", "UndefinedDomain"]:
                        # we are double-checking now that it's not a theme
                        theme_mapping = self.__get_theme(session.turn[-1].user_request.interaction.text)
                        if theme_mapping != "":
                            logger.info(f'Domain classification overriden due to theme match!')
                            confidence = "high"
                            top_domain = "DIYDomain"
                        else:
                            logger.info(f"DOMAIN CLASSIFICATION: {domain_response.confidence} {domain_response.domain}")

                    if top_domain in ["MedicalDomain", "FinancialDomain", "LegalDomain"]:

                        logger.info(f'Domain classification - Intent identified as {top_domain}')
                        rule = self.__get_rule(top_domain, confidence)
                        output.speech_text = random.choice(rule['response'][session.error_counter.no_match_counter])

                        # since we are not redirecting, we should increment the no match counter
                        if session.error_counter.no_match_counter < 2:
                            session.error_counter.no_match_counter += 1

                        if not session.headless:
                            self.__populate_screen(output.screen, current_theme)
                            if session.error_counter.no_match_counter > 0:
                                user_utterance = session.turn[-1].user_request.interaction.text
                                output.screen.headline = f'I understood: "{user_utterance}"'

                        # The role of this counter is to determine the Absolute Threshold to use, if we have High
                        # classification we don't want to change the confidence level required
                        if confidence == 'low':
                            session.task.state.domain_interaction_counter += 1

                        set_source(output)
                        return session, output

                if steps > 2:
                    # High Confidence
                    rule = self.__get_rule(top_domain, "high")
                else:
                    # High Confidence
                    rule = self.__get_rule(top_domain, confidence)

            # decide whether to redirect or not
            if trigger_theme or '[REDIRECT]' in rule['response']:
                # Assign domain to session and reroute to planning
                logger.info(f"phase change from domain to planner because - theme is triggered: {trigger_theme}, "
                            f"and rule is {rule['response']}, and redirect response is: "
                            f"{'[REDIRECT]' in rule['response']} ")
                if top_domain == "CookingDomain" or trigger_theme:
                    self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.COOKING)
                else:
                    self.__raise_phase_change(session, Task.TaskPhase.PLANNING, Session.Domain.DIY)

            # following the rulebook, we say something to get the user back on track
            output.speech_text = random.choice(rule['response'][session.error_counter.no_match_counter])

        # since we are not redirecting, we should increment the no match counter
        if session.error_counter.no_match_counter < 2:
            session.error_counter.no_match_counter += 1

        if not session.headless:
            self.__populate_screen(output.screen, current_theme)
            if session.error_counter.no_match_counter > 0:
                user_utterance = session.turn[-1].user_request.interaction.text
                output.screen.headline = f'I understood: "{user_utterance}"'

        # The role of this counter is to determine the Absolute Threshold to use, if we have High classification
        # we don't want to change the confidence level required
        if confidence == 'low':
            session.task.state.domain_interaction_counter += 1

        set_source(output)
        return session, output
