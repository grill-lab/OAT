import os
import random
import grpc

from typing import Optional, Tuple

from analytics.general.safety_parser import SafetyParser
from exceptions import PhaseChangeException
from personality_pb2 import PersonalityRequest
from personality_pb2_grpc import PersonalityStub
from taskmap_pb2 import OutputInteraction, Session, SessionState, Task
from utils import (
    UNSAFE_BOT_RESPONSE,
    close_session,
    filter_speech_text,
    is_in_user_interaction,
    logger,
    repeat_screen_response,
    set_source,
    SAFE_FALLBACK_RESPONSE
)

from .abstract_policy import AbstractPolicy
from .domain_policy import DefaultPolicy as DefaultDomainPolicy
from .execution_policy import DefaultPolicy as DefaultExecutionPolicy
from .farewell_policy import DefaultPolicy as DefaultFarewellPolicy
from .intents_policy import DefaultPolicy as DefaultIntentsPolicy
from .planning_policy import DefaultPolicy as DefaultPlanningPolicy
from .resuming_policy import DefaultPolicy as DefaultResumePolicy
from .validation_policy import DefaultPolicy as DefaultValidationPolicy


class PhasedPolicy(AbstractPolicy):
    """Top-level policy responsible for generating a response to a client request.

    The PhasedPolicy manages the process of passing the current ``Session`` object to the appropriate
    sub-policy or sub-policies. After a couple of checks for e.g. a "StopIntent" or an unsafe user
    utterance, the ``step`` method of the class will call the ``__route_policy`` method to decide
    which sub-policy should deal with the current request given the Session state. 

    Note that ``__route_policy`` may receive ``PhaseChangeExceptions`` from a policy to signal that
    the phase of the Session has been updated, and it should now be passed on to a different sub-policy.
    For example, an initial utterance of "pasta" will be initially routed to the DomainPolicy, where a
    ``PhaseChangeException`` will be triggered once the domain is recognised as "cooking". This in turn
    will cause another call to ``__route_policy`` which will now direct the Session to the PlanningPolicy.
    """

    def __init__(self):
        self.recursive_depth = 0
        self.domain_policy = DefaultDomainPolicy()
        self.planner_policy = DefaultPlanningPolicy()
        self.validation_policy = DefaultValidationPolicy()
        self.execution_policy = DefaultExecutionPolicy()
        self.farewell_policy = DefaultFarewellPolicy()
        self.resume_policy = DefaultResumePolicy()
        self.intents_policy = DefaultIntentsPolicy()

        self.safety_parser = SafetyParser()

    def __handle_user_utterance_safety(self, session: Session) -> Optional[OutputInteraction]:
        """Check if the current user utterance triggers any safety checks. 

        This method extracts the utterance text from the Session and uses the SafetyService in
        ``functionalities`` to check for different problems (suicidal intent, privacy, etc.).

        If the text is empty, all tests will always pass. 

        If any of the tests are triggered, an ``OutputInteraction`` will be created and returned. 

        Args:
            session (Session): the current Session object

        Returns:
            OutputInteraction if any checks trigger, None otherwise
        """
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
            set_source(safe_response)
            return safe_response

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['PrivacyViolationIntent',
                                                  'SensitivityViolationIntent',
                                                  'OffensiveIntent',
                                                  ]):
            safe_response.speech_text = random.choice(SAFE_FALLBACK_RESPONSE)
            safe_response = repeat_screen_response(session, safe_response)
            set_source(safe_response)
            return safe_response

        return None

    def __check_bot_safety(self, session: Session, output_interaction: OutputInteraction) -> OutputInteraction:
        """Checks the system response for safety issues.

        This method is called just before returning a response to the orchestrator.
        If any of the safety checks are triggered, the original response is overwritten
        by the ``UNSAFE_BOT_RESPONSE`` text, otherwise the existing response is unaltered.

        Args:
            session (Session): the current Session object
            output_interaction (OutputInteraction): the system response to be checked

        Returns:
            OutputInteraction: either the original object or an updated one with the unsafe response text
        """

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
        """Checks if the current session should be closed.

        This method will check if the latest user utterance indicates a desire to end the session.

        It will first check for a "StopIntent" in the current ``InputInteraction`` object, and
        return True if one exists. If that fails, it will check for any occurrence of the words
        and phrases in ``stop_sequences`` and return True if any match is found.

        Args:
            session (Session): the current Session object

        Returns:
            bool: True if a "stop intent" is found, False otherwise
        """

        last_interaction = session.turn[-1].user_request.interaction

        stop_sequences = ['end this', 'end the', 'finish', 'terminate', "don't talk",
                          'not talk', 'why are you still speaking', 'why are you still talking', 'shut up',
                          'zip it', 'make it end', 'go away', 'piss off', 'keep quiet', "shush"]

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
    def __handle_personality(session: Session) -> Optional[OutputInteraction]:
        """Checks if the current utterance should trigger the OAT's "personality" response.

        This method is intended to handle responses to questions like "what are you", "who
        made you", etc. 

        The utterance is checked by an RPC to the ``PersonalityProcessor`` class in ``functionalities``. 

        If the check fails, None is returned. If the check succeeds, then the text returned by
        ``PersonalityProcessor`` is used to populate and return a new ``OutputInteraction``.

        Args:
            session (Session): the current Session object

        Returns:
            A new OutputInteraction if a personality utterance is detected, None otherwise

        """
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
            output_interaction.screen.ParseFromString(
                session.turn[-2].agent_response.interaction.screen.SerializeToString())

        set_source(output_interaction)
        return output_interaction

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Called by the orchestrator to generate a system response to a request.

        This method is the entrypoint from the orchestrator into the policy package. It follows a simple
        process for each request:

        #. Safety check user utterance
        #. Check if a bot personality response is required
        #. Check if the user utterance indicates the session should stop
        #. Generate a response from one or more multiple sub-policies
        #. Check the response for safety
        #. Return response to the orchestrator

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, updated OutputInteraction)
        """
        self.recursive_depth = 0  # counts the number of recursive calls made via PhaseChangeException

        # --- Check safety of user utterance --- #
        agent_response = self.__handle_user_utterance_safety(session)
        # If user utterance is not safe --> respond with default prompts.
        if agent_response is not None:
            logger.warning('user utterance is not safe -> returning default response.')
            return session, agent_response

        # Here we handle OAT's personality which includes proper handling of sensitive and private information
        personality_response = self.__handle_personality(session)
        if personality_response is not None:
            return session, personality_response

        # Generate agent response based on policy.
        if self.__stop_intent(session):
            # session.state = SessionState.RESUME
            session, agent_response = self.farewell_policy.step(session)
        else:
            session, agent_response = self.__route_policy(session)

        if not session.greetings and not session.state == SessionState.CLOSED:
            if session.task.taskmap.title != '':
                greetings = f"Hi, welcome back, let’s continue with " \
                            f"{session.task.taskmap.title}! "
            else:
                greetings = f"Hi and welcome! "
            agent_response.speech_text = greetings + agent_response.speech_text
            session.greetings = True

        # filter for speech output failures
        agent_response.speech_text = filter_speech_text(agent_response.speech_text)

        if not session.headless:
            user_utterance = session.turn[-1].user_request.interaction.text
            agent_response.screen.subheader = f'I understood: "{user_utterance}"'

        agent_response = self.__check_bot_safety(session, agent_response)
        return session, agent_response

    def __route_policy(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Handles routing of Sessions to the appropriate policies.

        This method is responsible for routing a Session to the correct policy to generate a response,
        given the current state of the Session. This is usually done by checking the value of
        ``Session.state`` or ``Session.task.phase`, but the ``IntentsPolicy`` is slightly different
        in that it checks if any of the intents it can handle exist in the current interaction. If
        so the response comes from that policy regardless of the state/phase.

        The method also sets up a ``PhaseChangeException`` handler. This is used to catch exceptions
        raised by policies which signal that the request/session should now be handed over to another
        policy for further processing before it is returned. This currently results in a recursive call
        to this method, requiring the tracking of recursive depth. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, updated OutputInteraction)
        """

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
            assert self.recursive_depth < 5, "Maximum Recursive Depth exceed, there may be an infinite loop"

            return self.__route_policy(session)
