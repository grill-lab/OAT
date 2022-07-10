from taskmap_pb2 import Session, OutputInteraction, SessionState
from .abstract_policy import AbstractPolicy
from taskmap_pb2 import Task, OutputInteraction
from safety_pb2_grpc import SafetyStub
from safety_pb2 import SafetyAssessment, SafetyUtterance
from personality_pb2_grpc import PersonalityStub
from personality_pb2 import PersonalityRequest, PersonalityResponse

from .domain_policy import DefaultPolicy as DefaultDomainPolicy
from .planning_policy import DefaultPolicy as DefaultPlanningPolicy
from .validation_policy import DefaultPolicy as DefaultValidationPolicy
from .execution_policy import DefaultPolicy as DefaultExecutionPolicy
from .farewell_policy import DefaultPolicy as DefaultFarewellPolicy
from .resuming_policy import DefaultPolicy as DefaultResumePolicy
from .intents_policy import DefaultPolicy as DefaultIntentsPolicy
# from .elicitation_policy import DefaultPolicy as DefaultElicitationPolicy
# from .theme_policy import DefaultPolicy as DefaultThemePolicy

from exceptions import PhaseChangeException
import grpc

import os
import random
from utils import logger, close_session, repeat_screen_response, is_in_user_interaction, filter_speech_text
from typing import Optional
from analytics.general.safety_parser import SafetyParser
from utils import UNSAFE_BOT_RESPONSE


class PhasedPolicy(AbstractPolicy):

    def __init__(self):
        self.recursive_depth = 0
        self.domain_policy = DefaultDomainPolicy()
        self.planner_policy = DefaultPlanningPolicy()
        self.validation_policy = DefaultValidationPolicy()
        self.execution_policy = DefaultExecutionPolicy()
        self.farewell_policy = DefaultFarewellPolicy()
        self.resume_policy = DefaultResumePolicy()
        self.intents_policy = DefaultIntentsPolicy()
        # self.elicitation_policy = DefaultElicitationPolicy()
        # self.theme_policy = DefaultThemePolicy()

        self.safety_parser = SafetyParser()

    def __handle_user_utterance_safety(self, session) -> Optional[OutputInteraction]:
        """ Handle the safety of the user input. If unsafe return a default safety responses, otherwise [SAFE] token to
        indicate that the phase policy should be initiated. """
        user_interaction = session.turn[-1].user_request.interaction
        safe_response = OutputInteraction()

        # If input text is empty, we don't need to check for safety
        if user_interaction.text == '':
            return None

        # Parses the
        self.safety_parser(session)

        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['SuicideIntent']):
            safe_response.speech_text = "It might not always feel like it, but there are people who can help. " \
                                        "Please know that you can call the National Suicide Prevention Lifeline, " \
                                        "twenty-four hours a day, seven days a week. Their number is, " \
                                        "1-800-273-8255. Again, that’s 1-800-273-8255."
            session, safe_response = close_session(session, safe_response)
            return safe_response

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['PrivacyViolationIntent',
                                                  'SensitivityViolationIntent',
                                                  'OffensiveIntent',
                                                  ]):
            safe_response.speech_text = "I don’t feel comfortable talking about that. What else can I help you with?"
            safe_response = repeat_screen_response(session, safe_response)
            return safe_response

        return None

    def __check_bot_safety(self, session, output_interaction):

        (
            privacy_safe,
            sensitivity_safe,
            offensive_speech_safe,
            suicide_prevention_safe
        ) = self.safety_parser.check_utterance(output_interaction.speech_text)

        if not privacy_safe or \
                not sensitivity_safe or \
                not offensive_speech_safe or \
                not suicide_prevention_safe:
            output_interaction.speech_text = random.choice(UNSAFE_BOT_RESPONSE)
            output_interaction = repeat_screen_response(session, output_interaction)

        return output_interaction

    @staticmethod
    def __stop_intent(session: Session) -> bool:

        last_interaction = session.turn[-1].user_request.interaction

        stop_sequences = ['end this', 'end the', 'finish', 'terminate', "don't talk",
            'not talk', 'why are you still speaking', 'why are you still talking', 'shut up',
                'zip it', 'make it end', 'go away', 'piss off', 'keep quiet', "shush"
        ]

        # check if we have a stop intent First
        if "StopIntent" in last_interaction.intents:
            return True

        # check for a stop sequence
        else:
            for stop_word_or_sentence in stop_sequences:
                stop_word_or_sentence = stop_word_or_sentence.lower()
                words = stop_word_or_sentence.split()
                
                if len(words) > 1:
                    stop_sentence = stop_word_or_sentence
                    if stop_sentence in last_interaction.text.lower():
                        logger.info(f"'{stop_sentence}' matched '{last_interaction.text}' as a stop sentence")
                        return True

                else:
                    stop_word = stop_word_or_sentence
                    tokenized_user_utterance = last_interaction.text.lower().split()
                    if stop_word in tokenized_user_utterance:
                        logger.info(f"'{stop_word}' matched '{last_interaction.text}' as a stop word")
                        return True
        
        return False

    @staticmethod
    def __handle_personality(session: Session) -> PersonalityResponse:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        personality = PersonalityStub(channel)

        # Build utterance as input to safety check functionalities.
        request = PersonalityRequest()
        request.utterance = session.turn[-1].user_request.interaction.text

        response = personality.process_utterance(request)

        if not response.is_personalilty_question:
            return None

        output_interaction = OutputInteraction()
        output_interaction.speech_text = response.answer
        if not session.headless and len(session.turn) > 1:
            output_interaction.screen.ParseFromString(session.turn[-2].agent_response.interaction.screen.SerializeToString())

        return output_interaction

    def step(self, session: Session) -> (Session, OutputInteraction):
        """ Take a policy step and update the session and generate a agent response to present to the user. """
        self.recursive_depth = 0  # counts the number of recursive calls made via PhaseChangeException

        # --- Check safety of user utterance --- #
        agent_response = self.__handle_user_utterance_safety(session)
        # If user utterance is not safe --> respond with default prompts.
        if agent_response is not None:
            logger.warning('user utterance is not safe -> returning default response.')
            return session, agent_response

        # Here we handle the bot's personality which includes proper handling of sensitive and private information
        personality_response = self.__handle_personality(session)
        if personality_response is not None:
            return session, personality_response

        # Generate agent response based on policy.
        if self.__stop_intent(session):
            session, agent_response = self.farewell_policy.step(session)
        else:
            session, agent_response = self.__route_policy(session)

        if not session.greetings and not session.state == SessionState.CLOSED:
            # if not session.resume_task:
            #     greetings = "Hi, this is an Alexa Prize TaskBot. "
            # elif session.task.taskmap.title != '':
            #     greetings = f"Hi, this is an Alexa Prize TaskBot, welcome back, let’s continue with " \
            #                 f"{session.task.taskmap.title}! "
            # else:
            #     greetings = f"Hi, this is an Alexa Prize TaskBot, welcome back! "
            # agent_response.speech_text = greetings + agent_response.speech_text
            agent_response.speech_text = agent_response.speech_text
            session.greetings = True

        # filter for speech output failures
        agent_response.speech_text = filter_speech_text(agent_response.speech_text)

        if not session.headless:
            user_utterance = session.turn[-1].user_request.interaction.text
            agent_response.screen.subheader = f'I understood: "{user_utterance}"'

        agent_response = self.__check_bot_safety(session, agent_response)
        return session, agent_response

    def __route_policy(self, session: Session) -> (Session, OutputInteraction):

        try:
            if self.intents_policy.triggers(session):
                return self.intents_policy.step(session)
            elif session.state != SessionState.RUNNING:
                # CALL RESUME POLICY
                return self.resume_policy.step(session)
            elif session.task.phase == Task.TaskPhase.DOMAIN:
                # CALL DOMAIN POLICY
                return self.domain_policy.step(session)
            elif session.task.phase == Task.TaskPhase.PLANNING:
                # CALL PLANNING POLICY
                return self.planner_policy.step(session)
            # elif session.task.phase == Task.TaskPhase.ELICITING:
            #     # CALL ELICITATION POLICY
            #     return self.elicitation_policy.step(session)
            # elif session.task.phase == Task.TaskPhase.THEME:
            #     # CALL THEME POLICY
            #     return self.theme_policy.step(session)
            elif session.task.phase == Task.TaskPhase.VALIDATING:
                # CALL VALIDATION POLICY
                return self.validation_policy.step(session)
            elif session.task.phase == Task.TaskPhase.EXECUTING:
                # CALL EXECUTION POLICY
                return self.execution_policy.step(session)
            elif session.task.phase == Task.TaskPhase.CLOSING:
                # CALL FAREWELL POLICY
                return self.farewell_policy.step(session)
            else:
                logger.error("Invalid field for Task Phase")
                raise Exception("Invalid Task Phase")

        except PhaseChangeException:
            # Catch every Phase changes and reroute the call to the correct policy

            self.recursive_depth += 1
            assert self.recursive_depth < 3, "Maximum Recursive Depth exceed, there may be an infinite loop"

            return self.__route_policy(session)
