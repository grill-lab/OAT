import os
import random
import re
import grpc

from typing import List, Tuple
from datetime import datetime, timedelta

from exceptions import PhaseChangeException
from phase_intent_classifier_pb2 import IntentRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from policy.abstract_policy import AbstractPolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from policy.chitchat_policy import DefaultPolicy as DefaultChitChatPolicy

from task_manager_pb2 import InfoRequest, InfoResponse, TMRequest, TMResponse
from task_manager_pb2_grpc import TaskManagerStub
from taskmap_pb2 import OutputInteraction, ScreenInteraction, Session, Task, Video, Image, SessionState

from compiled_protobufs.llm_pb2_grpc import LLMExecutionSearchManagerStub
from compiled_protobufs.llm_pb2 import ExecutionSearchRequest, ExecutionSearchResponse

from utils import (
    ASR_ERROR,
    PAUSING_PROMPTS,
    RIND_FALLBACK_RESPONSE,
    build_video_button,
    consume_intents,
    is_in_user_interaction,
    logger,
    repeat_screen_response,
    set_source,
    show_ingredients_screen,
    NO_VIDEO,
    EXECUTION_START_INTRO,
    build_chat_screen,
    should_trigger_theme,
    DIY_FAREWELL, COOKING_FAREWELL, SEARCH_AGAIN_QUESTION, DECLINE_NEW_SEARCH,
    NO_MORE_DETAILS, HELPFUL_PROMPT_PAIRS, JOKE_TRIGGER_WORDS
)
from video_searcher_pb2 import TaskStep, VideoQuery
from video_searcher_pb2_grpc import ActionClassifierStub, VideoSearcherStub
from compiled_protobufs.theme_pb2 import ThemeRequest
from compiled_protobufs.database_pb2_grpc import DatabaseStub

from .actions import perform_action
from .condition_policy import ConditionPolicy
from .extra_info_policy import ExtraInfoPolicy


def route_to_domain(session):
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["CancelIntent", "YesIntent"])
    cancel = is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['Consumed.CancelIntent'])
    consume_intents(session.turn[-2].user_request.interaction,
                    intents_list=["SearchIntent"])
    session.task_selection.preferences_elicited = False
    session.task.state.help_corner_active = False
    session.task.state.joke_uttered = False
    session.task.state.tip_uttered = False
    session.task_selection.elicitation_turns = 0
    session.task_selection.categories_elicited = 0
    session.task_selection.results_page = 0
    session.domain = Session.Domain.UNKNOWN
    del session.task_selection.elicitation_utterances[:]
    session.task_selection.theme.Clear()
    session.task_selection.category.Clear()
    del session.task_selection.candidates_union[:]
    session.task.taskmap.Clear()
    session.task.state.Clear()
    session.task.phase = Task.TaskPhase.DOMAIN

    del session.turn[-1].user_request.interaction.intents[:]
    if len(session.turn) > 1:
        del session.turn[-2].user_request.interaction.intents[:]
        if len(session.turn[-2].user_request.interaction.params) > 0:
            if 'search' in session.turn[-2].user_request.interaction.params[0]:
                session.turn[-1].user_request.interaction.text = session.turn[-2].user_request.interaction.text
                session.turn[-1].user_request.interaction.intents.append('SearchIntent')
    if cancel:
        session.turn[-1].user_request.interaction.intents.append('Consumed.CancelIntent')
    raise PhaseChangeException()


def route_to_planning(session: Session) -> None:
    """Redirect control of the response to the PlanningPolicy.

    This method will consume any CancelIntent/NoIntent/PreviousIntent in the
    current InputInteraction, reset ``session.task.phase`` to PLANNING and then
    raise a PhaseChangeException to cause the PlanningPolicy to be activated again.

    Args:
        session (Session): the current Session object

    Returns:
        Nothing, raises PhaseChangeException
    """
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["PreviousIntent"])
    session.task.phase = Task.TaskPhase.PLANNING
    session.task.state.Clear()

    session.task.state.requirements_displayed = False
    session.task.state.validation_courtesy = False
    session.task.state.help_corner_active = False
    session.task.state.validation_page = 0
    session.task_selection.results_page = 0
    session.task.taskmap.Clear()
    raise PhaseChangeException()


class ExecutionPolicy(AbstractPolicy):
    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        external_channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])

        self.task_manager = TaskManagerStub(channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)
        self.video_searcher = VideoSearcherStub(neural_channel)
        self.action_classifier = ActionClassifierStub(channel)
        self.qa_policy = DefaultQAPolicy()
        self.chitchat_policy = DefaultChitChatPolicy()
        self.llm_search_classification = LLMExecutionSearchManagerStub(channel)

        self.condition_policy = ConditionPolicy()
        self.extra_info_policy = ExtraInfoPolicy()
        self.database = DatabaseStub(external_channel)

        self.search_triggered = False

    def __check_and_perform_actions(self, session: Session, output: OutputInteraction) -> None:
        """Check if there are actions to perform and if so perform them.

        Makes a call to the TaskManager service to retrieve a list of Actions
        for the current task, then calls ``perform_action`` on each.
        Args:
            session (Session): the current Session object
            output (OutputInteraction): the current OutputInteraction object

        Returns:
            Nothing
        """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString()
        )
        request.state.ParseFromString(
            session.task.state.SerializeToString()
        )
        actions_response: InfoResponse = self.task_manager.get_actions(request)

        if actions_response.unresolved_statements:
            logger.info(f"Found {len(actions_response.unresolved_statements)} Actions to perform!!")
            for action_statement in actions_response.unresolved_statements:
                perform_action(session, output, action_statement)

    def __get_requirements_utterances(self, session: Session, local: bool) -> List[str]:
        """Build list of utterances to to convey task requirements to user.

        Args:
            session (Session): the current Session object
            local (bool): TODO

        Returns:
            List[str]: a list of strings containing the requirements
        """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString())

        # TODO what does local mean here?
        if local:
            request.local = local
            request.state.ParseFromString(session.task.state.SerializeToString())

        requirements_response: InfoResponse = self.task_manager.get_requirements(
            request)
        requirements_list: List[str] = []
        for requirement in requirements_response.unresolved_statements:
            if requirement.amount != " " and not local:
                requirements_list.append(requirement.amount + " " + requirement.body)
            else:
                requirements_list.append(requirement.body)

        if len(requirements_list) > 0:
            logger.info(f'Requirements: {requirements_list}')
        else:
            logger.info("No requirements found")

        return requirements_list

    @staticmethod
    def __raise_phase_change(session: Session, phase: Task.TaskPhase.ValueType) -> None:
        """Raise a PhaseChangeException to switch the Session to a new phase.

        Args:
            session (Session): the current Session object
            phase (Task.TaskPhase): the TaskPhase value for the new phase

        Returns:
            Nothing (raises PhaseChangeException)
        """
        session.task.state.execution_ingredients_displayed = False
        # session.task.state.execution_tutorial_displayed = False
        session.task.phase = phase

        raise PhaseChangeException()

    def __retrieve_video(self, session: Session) -> Video:
        """Search for and return a video for the current step (if possible).

        This method will construct a query for the VideoSearcher service
        based on the current step text, and return the result.

        See the full description in doc/video_searcher_documentation.md.

        Args:
            session (Session): the current Session object

        Returns:
            Video: a possibly-empty Video protobuf object
        """
        # retrieve current step text
        request = TMRequest()
        request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
        request.state.ParseFromString(session.task.state.SerializeToString())

        step: TaskStep = TaskStep()
        video_message: Video = Video()

        try:
            step_output = self.task_manager.get_step(request)
            step.step_text = step_output.speech_text

            query: VideoQuery = VideoQuery()
            if step_output.screen.caption_query == '':
                action_classification = self.action_classifier.classify_action_step(step)
                logger.info(f'Step contains an action: {action_classification.is_action}')

                if action_classification.is_action:
                    query.text = random.choice(action_classification.methods)
                    query.top_k = 10
            else:
                query.text = step_output.screen.caption_query
                query.top_k = 10

            if query.text != "":
                best_video_match = self.video_searcher.search_video(query)

                if best_video_match.title != "":
                    logger.info(f'Found a video: {best_video_match.title}')
                    video_message.title = best_video_match.title
                    video_message.hosted_mp4 = f"https://sophie-video-project.s3.amazonaws.com/{best_video_match.hosted_mp4}"
                    video_message.doc_id = best_video_match.doc_id

            return video_message

        except Exception as e:
            logger.info(e)
            if "IndexError" in str(e):
                logger.warning("Tried to schedule a step that doesn't exist")

        return video_message

    @staticmethod
    def __retrieve_image(session: Session) -> Image:
        image: Image = Image()
        image.path = session.task.taskmap.thumbnail_url
        return image

    @staticmethod
    def __handle_help_screen(session: Session) -> None:
        if "_button" in session.turn[-1].user_request.interaction.text:
            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.append("InformIntent")
            raise PhaseChangeException()
        if session.turn[-1].user_request.interaction.intents[-1] == "PreviousIntent":
            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.append("RepeatIntent")
        session.task.state.help_corner_active = False

    def __get_theme_keywords(self) -> List[str]:

        request = ThemeRequest()

        relevant_dates = []
        now_date = datetime.today()
        for i in range(7):
            date = now_date + timedelta(days=i)
            relevant_dates.append(date.strftime("%d-%m-%Y"))

        # get themed holidays
        holiday_themes = []
        for date in relevant_dates:
            request.date = date
            theme = self.database.get_theme_by_date(request)
            if len(theme.queries) > 0:
                holiday_themes.extend([(date, theme_sug) for theme_sug in theme.queries])

        logger.info(f"Found date themes: {holiday_themes}")

        themes = ["Desserts"]
        themes.extend([theme_sug for date, theme_sug in holiday_themes if theme_sug != "current_recommendation"])

        return themes

    def manage_new_search_execution(self, session):

        request: ExecutionSearchRequest = ExecutionSearchRequest()
        request.domain = session.domain
        request.taskmap.MergeFrom(session.task.taskmap)
        request.last_last_agent_response = session.turn[-3].agent_response.interaction.speech_text
        request.last_user_response = session.turn[-2].user_request.interaction.text
        request.last_agent_response = session.turn[-2].agent_response.interaction.speech_text
        request.user_question = session.turn[-1].user_request.interaction.text
        request.timeout = 2000
        llm_classification: ExecutionSearchResponse = self.llm_search_classification.generate_decision(request)

        if llm_classification.intent_classification == "continue_current_task":
            logger.info('QA after LLM classification')
            self.search_triggered = False
            consume_intents(user_interaction=session.turn[-1].user_request.interaction,
                            intents_list=['SearchIntent'])
            output: OutputInteraction = OutputInteraction()
            _, output = self.qa_policy.step(session)
            output = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif llm_classification.intent_classification == "ask_clarifying_question":
            self.search_triggered = False
            output: OutputInteraction = OutputInteraction()
            consume_intents(user_interaction=session.turn[-1].user_request.interaction,
                            intents_list=['SearchIntent'])
            more_details_options = [
                "Interesting idea. Can you give me more details? ",
                "I am not sure I understand. Can you give me more details? ",
                "Do you want me to try and adjust the current task? ",
                "Are you asking a question about what we are currently doing? ",
            ]
            output.speech_text = random.choice(more_details_options)
            output = repeat_screen_response(session, output)
            set_source(output)
            return session, output
        else:
            logger.info('Normal new search in execution!')
            self.search_triggered = True
            output: OutputInteraction = OutputInteraction()
            output.speech_text = random.choice(SEARCH_AGAIN_QUESTION)
            output = repeat_screen_response(session, output)
            set_source(output)
            return session, output

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the ExecutionPolicy class.

        A summary of this method:

        - call the PhaseIntentClassifier if no intents already generated
        - call ConditionPolicy and return any non-None response it produces (these
          will occur if the current TaskMap step has a condition associated with it)
        - check for a range of specific intents/utterances, including
            - "play a video" => populate response with video if possible
            - Confused/TimerIntents => redirect to IntentsPolicy
            - YesIntent/NoIntent => call ExtraInfoPolicy
            - StopIntent => redirect to FarewellPolicy
            - PauseIntent => pause the session/task
            - CancelIntent => currently can't cancel mid-task
            - ShowRequirementsIntent => generate response listing requirements
            - DetailsIntent => show more detail for a step (if available)
        - Previous/Next/Repeat/GotoIntents will change (or repeat) the current step
          via the TaskManager
        - the remainder of the method deals with populating the OutputInteraction to return

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """

        if len(session.turn[-1].user_request.interaction.intents) == 0:
            intent_request = IntentRequest()
            for turn in session.turn:
                intent_request.turns.append(turn)

            output: OutputInteraction = OutputInteraction()

            intent_classification = (
                self.phase_intent_classifier.classify_intent(intent_request)
            )
            session.turn[-1].user_request.interaction.params.append(intent_classification.attributes.raw)

            translation_dict = {
                "select": "GoToIntent",
                "cancel": "CancelIntent",
                "restart": "CancelIntent",
                "search": "SearchIntent",
                "yes": "YesIntent",
                "no": "NoIntent",
                "repeat": "RepeatIntent",
                "confused": "ConfusedIntent",
                "show_more_results": "DetailsIntent",
                "show_requirements": "ShowRequirementsIntent",
                "show_more_details": "DetailsIntent",
                "next": "NextIntent",
                "previous": "PreviousIntent",
                "stop": "StopIntent",
                "chit_chat": "ChitChatIntent",
                "set_timer": "createTimerIntent",
                "stop_timer": "deleteTimerIntent",
                "pause_timer": "pauseTimerIntent",
                "resume_timer": "resumeTimerIntent",
                "show_timers": "showTimerIntent",
                "ASR_error": "ASRErrorIntent",
                "answer_question": "QuestionIntent",
                "inform_capabilities": "InformIntent",
                "step_select": "GoToIntent",
                "pause": 'PauseIntent',
                "start_task": 'YesIntent',
                "play_video": "VideoIntent"
            }

            intent_translation = translation_dict.get(intent_classification.classification)
            if intent_translation:
                session.turn[-1].user_request.interaction.intents.append(
                    intent_translation
                )
            else:
                output.speech_text = random.choice(RIND_FALLBACK_RESPONSE)
                output = repeat_screen_response(session, output)
                set_source(output)
                return session, output

        logger.info(f'INTENTS: {session.turn[-1].user_request.interaction.intents}')
        condition_text = None
        out_session, output = self.condition_policy.step(session)

        if out_session is not None and output is not None:
            # Check for actions to be performed
            self.__check_and_perform_actions(session, output)
            set_source(output)
            return out_session, output

        if session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:
            if "_button" in session.turn[-1].user_request.interaction.text \
                    and not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')
            self.__handle_help_screen(session)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ChitChatIntent', 'DetailsIntent']):
            # we have details/ chitchat and just came from farewell,
            # double check if it was maybe a search intent as this is a common miss classification

            theme_options = self.__get_theme_keywords()
            logger.info(theme_options)

            trigger_theme = False
            theme_title = ""
            for theme in theme_options:
                user_utterance = session.turn[-1].user_request.interaction.text
                trigger_theme, _ = should_trigger_theme(user_utterance=user_utterance,
                                                        theme_word=theme)
                if trigger_theme:
                    theme_title = theme
                    trigger_theme = True
                    break

            if trigger_theme:
                consume_intents(user_interaction=session.turn[-1].user_request.interaction,
                                intents_list=[intent for intent in session.turn[-1].user_request.interaction.intents])
                logger.info(f'Theme {theme_title} triggered, even though first classification '
                            f'was wrong: {session.turn[-1].user_request.interaction.intents}')
                del session.turn[-1].user_request.interaction.params[:]
                session.turn[-1].user_request.interaction.params.append(f'search("{theme_title}")')
                session.turn[-1].user_request.interaction.intents.append("SearchIntent")
                self.search_triggered = True

        if is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                  intents_list=["SearchIntent"]) and \
                is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                       intents_list=["YesIntent"]):
            # we failed to reroute to planning on the last farewell screen
            logger.info('We failed to reroute to planning from execution, manually correcting...')
            session.turn[-1].user_request.interaction.MergeFrom(session.turn[-2].user_request.interaction)
            output = OutputInteraction()
            route_to_domain(session)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["SearchIntent"]):
            if is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                      intents_list=['NoIntent']) and \
                    session.turn[-3].agent_response.interaction.speech_text == SEARCH_AGAIN_QUESTION:
                logger.info('Ignoring search classification, going to chit chat since repeated no')
                self.search_triggered = False
                session.turn[-1].user_request.interaction.intents.append("ChitChatIntent")
                consume_intents(user_interaction=session.turn[-1].user_request.interaction,
                                intents_list=['SearchIntent'])
            elif any([prompt in session.turn[-2].agent_response.interaction.speech_text for prompt in DIY_FAREWELL]) \
                    or any([prompt in session.turn[-2].agent_response.interaction.speech_text
                            for prompt in COOKING_FAREWELL]):
                self.search_triggered = False
                route_to_domain(session)
            else:
                session, output = self.manage_new_search_execution(session)
                return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["VideoIntent"],
                                  utterances_list=['play video', 'click the video button']):
            output = OutputInteraction()
            if session.headless:
                output.speech_text = "Sorry, we cannot play a video without a screen. Why don't you continue" \
                                     "with the recipe?"
            else:

                previous_agent_response = session.turn[-2].agent_response.interaction
                if previous_agent_response.screen.video.title != "":
                    output.screen.video.MergeFrom(
                        previous_agent_response.screen.video
                    )
                    output.screen.format = ScreenInteraction.ScreenFormat.VIDEO
                    output.idle_timeout = 1800
                    output.pause_interaction = True
                    output.speech_text = "Playing video now..."
                else:
                    # we didn't find a relevant video to play
                    output: OutputInteraction = repeat_screen_response(session, output)
                    output.speech_text = NO_VIDEO

            set_source(output)
            return session, output

        elif (is_in_user_interaction(session.turn[-1].user_request.interaction,
                                     intents_list=['NoIntent']) and self.search_triggered == True):
            self.search_triggered = False
            output: OutputInteraction = OutputInteraction()
            output.speech_text = random.choice(DECLINE_NEW_SEARCH)
            output: OutputInteraction = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["YesIntent"]) and self.search_triggered:

            self.search_triggered = False
            route_to_domain(session)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ConfusedIntent",
                                                  "createTimerIntent",
                                                  "pauseTimerIntent",
                                                  "deleteTimerIntent",
                                                  "resumeTimerIntent",
                                                  "showTimerIntent",
                                                  "InformIntent"]):
            # this will bounce things back to PhasedPolicy, where the next call to
            # __route_policy will trigger the IntentsPolicy with one of the above
            # intents
            if "Step" in session.turn[-2].agent_response.interaction.speech_text:
                session.task.state.in_farewell = False
            else:
                session.task.state.in_farewell = True
            raise PhaseChangeException()

        # if there is a video available, then handle Yes Intent as play video intent
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["YesIntent"]) \
                and session.turn[-2].agent_response.interaction.screen.video.title != "":

            output = OutputInteraction()
            output.screen.video.MergeFrom(
                session.turn[-2].agent_response.interaction.screen.video
            )
            output.screen.format = ScreenInteraction.ScreenFormat.VIDEO
            output.idle_timeout = 1800
            output.pause_interaction = True
            output.speech_text = "Playing video now..."
            set_source(output)

            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["YesIntent", "NoIntent",
                                                  "NextIntent"]) and session.task.state.extra_info_unresolved:
            _, output = self.extra_info_policy.step(session)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['StopIntent']):
            self.__raise_phase_change(session, phase=Task.TaskPhase.CLOSING)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['QuestionIntent']):
            session.task.state.extra_info_unresolved = False
            _, output = self.qa_policy.step(
                session
            )
            user_utterance = session.turn[-1].user_request.interaction.text
            output = build_chat_screen(policy_output=output, user_utterance=user_utterance, session=session)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['ChitChatIntent']) or \
                (session.turn[-2].agent_response.interaction.speech_text.endswith('?') and \
                 not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                            intents_list=['NextIntent', 'StopIntent', 'PreviousIntent', 'CancelIntent',
                                                          'ShowRequirementsIntent'])):
            # if we had a system initiative question or a joke (that ends with ?), we want to answer with chit chat
            session, output = self.chitchat_policy.step(
                session
            )
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['ASRErrorIntent']):
            output: OutputInteraction = OutputInteraction()
            user_utterance = session.turn[-1].user_request.interaction.text
            output.speech_text = random.choice(ASR_ERROR).format(user_utterance)
            output = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["CancelIntent"]):
            route_to_domain(session)

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

        elif (is_in_user_interaction(session.turn[-1].user_request.interaction,
                                     intents_list=['NoIntent'])
              and not session.task.state.extra_info_unresolved and condition_text is None and output is None):

            previous_agent_response = session.turn[-2].agent_response.interaction
            output: OutputInteraction = OutputInteraction()

            if previous_agent_response.screen.video.title == "" \
                    and not previous_agent_response.speech_text == SEARCH_AGAIN_QUESTION:
                output.idle_timeout = 1800
                output.pause_interaction = True
                if session.headless:
                    output.idle_timeout = 1800
                    output.pause_interaction = True
                    paused = [
                        "I have paused the conversation",
                        "conversation paused",
                        "paused for now, wake me if you need me!"
                    ]
                    output.speech_text = random.sample(paused, 1)[0]
                else:
                    output.speech_text = "I have paused the conversation. " \
                                         "If you want to speak to me again just wake me."
            else:
                output.speech_text = random.choice(DECLINE_NEW_SEARCH)
            output: OutputInteraction = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['ShowRequirementsIntent'],
                                    utterances_list=['show me the ingredients']):
            requirements_list = self.__get_requirements_utterances(session, local=False)

            output: OutputInteraction = OutputInteraction()
            if not session.headless:
                output: OutputInteraction = show_ingredients_screen(session, requirements_list, output)
                # add start with task button
                output.screen.buttons.append("Continue")
                output.screen.on_click_list.append("repeat")

            output.speech_text = ''
            if requirements_list == []:
                output.speech_text += "This task has no requirements. You can say 'next' to keep going," \
                                      "or say 'repeat' to hear the step again."
            else:
                if session.headless:
                    output.speech_text = f'For {session.task.taskmap.title}, you need: {". ".join(requirements_list)}. '
                else:
                    output.speech_text = f'Here are the task requirements for {session.task.taskmap.title}. '

                output.speech_text += 'You can navigate back to the task by saying "Go back"'

            session.task.state.execution_ingredients_displayed = True
            set_source(output)
            return session, output

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['DetailsIntent'],
                                    utterances_list=['more details', 'details', 'show me more']):
            request = TMRequest()
            request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
            request.state.ParseFromString(session.task.state.SerializeToString())
            request.taskmap.headless = session.headless

            output: OutputInteraction = self.task_manager.more_details(request)
            if any([prompt in output.speech_text for prompt in NO_MORE_DETAILS]):
                # no more details found, so query chit chat
                session, output = self.qa_policy.step(session)
                output = repeat_screen_response(session, output)
                del output.screen.paragraphs[:]
                new_screen_text = output.speech_text
                for keyword, text in HELPFUL_PROMPT_PAIRS:
                    if text in new_screen_text:
                        new_screen_text = new_screen_text.replace(text, "")
                        break

                output.screen.paragraphs.append(new_screen_text)

            if not session.headless:

                previous_agent_response = session.turn[-2].agent_response.interaction
                if previous_agent_response.screen.video.title != "":
                    output.screen.video.MergeFrom(previous_agent_response.screen.video)
                    speech_text, screen = build_video_button(output, output.screen.video)
                    output.screen.ParseFromString(screen.SerializeToString())
                else:
                    # search for video
                    found_video: Video = self.__retrieve_video(session)
                    output.screen.video.MergeFrom(found_video)
                    speech_text, screen = build_video_button(output, found_video)
                    output.screen.ParseFromString(screen.SerializeToString())
                    output.speech_text += speech_text

            output.idle_timeout = 1800
            output.pause_interaction = True
            set_source(output)
            return session, output

        else:

            request = TMRequest()
            request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
            request.state.ParseFromString(session.task.state.SerializeToString())
            request.taskmap.headless = session.headless

            try:
                session.task.state.video_uttered = (len(session.turn) >= 2 and session.turn[
                    -2].agent_response.interaction.screen.video.title != "") or session.task.state.video_uttered
                request.video_suggested = session.task.state.video_uttered
            except Exception as e:
                logger.warning("video_suggested field non-existent in request")

            try:
                if session.task.state.execution_ingredients_displayed:
                    session.task.state.execution_ingredients_displayed = False
                    request.state.execution_ingredients_displayed = False
                    tm_response: TMResponse = self.task_manager.repeat(request)

                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['PreviousIntent']):
                    if session.task.state.index_to_next > 1 and not is_in_user_interaction(
                            session.turn[-1].user_request.interaction,
                            utterances_list=['previous screen']):
                        tm_response: TMResponse = self.task_manager.previous(request)
                    else:
                        if is_in_user_interaction(session.turn[-1].user_request.interaction,
                                                  utterances_list=['previous screen']) and \
                                is_in_user_interaction(session.turn[-2].user_request.interaction,
                                                       intents_list=['QuestionIntent'],
                                                       utterances_list=JOKE_TRIGGER_WORDS):
                            # if we decide to close the joke and QA screen
                            tm_response: TMResponse = self.task_manager.repeat(request)
                        else:
                            route_to_planning(session)
                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['RepeatIntent']):
                    tm_response: TMResponse = self.task_manager.repeat(request)
                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['GoToIntent']):
                    request.attribute = intent_classification.attributes.step
                    tm_response: TMResponse = self.task_manager.go_to(request)

                else:
                    tm_response: TMResponse = self.task_manager.next(request)

            except grpc.RpcError as e:
                if "EndOfExecutionException" in e.details():
                    logger.warning(
                        "Exception on getting the next step, "
                        "we reached the end of execution"
                    )

                    # This will mean that most likely we don't have any more steps to execute
                    self.__raise_phase_change(session, phase=Task.TaskPhase.CLOSING)

                else:
                    logger.exception("Unknown error ", exc_info=e)
                    raise e

            session.task.state.ParseFromString(
                tm_response.updated_state.SerializeToString()
            )
            output = tm_response.interaction

            if len(output.screen.image_list) == 0:
                image = self.__retrieve_image(session)
                output.screen.image_list.append(image)

            requirements_list = self.__get_requirements_utterances(session, local=True)
            if requirements_list:
                logger.info(f"requirement list {requirements_list}")
                for req in requirements_list:
                    output.screen.requirements.append(req)

            condition_text = self.condition_policy.get_condition(session)
            if condition_text is not None:
                output.speech_text += " " + condition_text

            if not session.headless and session.task.state.condition_id_eval == "":
                if output.screen.video.title == "":
                    found_video: Video = self.__retrieve_video(session)

                    if found_video.title != "":
                        logger.info(f'FOUND VIDEO: {found_video.title}')
                        output.screen.video.MergeFrom(found_video)
                        speech_text, screen = build_video_button(output, found_video)
                        output.screen.ParseFromString(screen.SerializeToString())
                        output.speech_text += speech_text

            if output.screen.hint_text != "":
                hint_text_options = [output.screen.hint_text]
            else:
                hint_text_options = []

            if len(requirements_list) > 0:
                short_reqs = [req for req in requirements_list if len(req) < 15]
                if len(short_reqs) > 0:
                    hint_text_options.append(f"how much {random.choice(short_reqs)} do I need? ")
                    hint_text_options.append(f"how much {random.choice(short_reqs)}? ")
                    hint_text_options.append(f"why do I need {random.choice(short_reqs)}? ")
                    hint_text_options.append(f"can I replace {random.choice(short_reqs)}? ")
            hint_text_options.append(f"what is special about this step? ")
            hint_text_options.append("what can do you")

            output.screen.hint_text = random.choice(hint_text_options)
            logger.info(f'HINT TEXT: {output.screen.hint_text}')

            if condition_text is None and session.task.state.condition_id_eval == "" and output.screen.video.title == "" and session.task.state.index_to_next > 1:
                speech_length = len(re.findall(r'\w+', output.speech_text))
                lower_bound = 6
                upper_bound = 50

                if (speech_length < lower_bound) or \
                        (lower_bound <= speech_length < upper_bound and random.uniform(0, 1) < 0.6):
                    extra_info_text, image_url = self.extra_info_policy.get_extra_information(session)
                    output.speech_text += extra_info_text

                    if image_url != "":
                        step_image = output.screen.image_list[0]
                        del output.screen.image_list[:]
                        joke_image: Image = Image()
                        joke_image.path = image_url
                        output.screen.image_list.append(joke_image)
                        output.screen.image_list.append(step_image)

            if not session.task.state.execution_tutorial_displayed:
                session.task.state.execution_tutorial_displayed = True
                task_type: str = "recipe" if session.domain == Session.Domain.COOKING else "task"
                output.speech_text = random.choice(EXECUTION_START_INTRO).format(task_type) + output.speech_text

        output.idle_timeout = 10
        if not session.headless and condition_text is None:
            output.idle_timeout = 1800
            output.pause_interaction = True

        # Tutorial utterances can be inserted in the re-prompted speech, that is read after
        # a few seconds of silence from the user. This achieves that if he does not know what to do,
        # we guide him on the operations that can be done during execution

        TUTORIAL1 = 'You can navigate through the steps by saying "Next", "Previous" or "Repeat", ' \
                    'or you can go back to the search results by saying "cancel".'

        TUTORIAL2 = 'You can ask any question about the requirements and steps if you have any doubts. ' \
                    'I can also repeat the last instruction if you say "Repeat".'

        tutorial_list = [TUTORIAL1, TUTORIAL2]

        chosen_tutorial = random.sample(tutorial_list, 1)[0]
        output.reprompt = chosen_tutorial

        self.__check_and_perform_actions(session, output)
        set_source(output)
        return session, output
