import os
import random
import grpc

from typing import Tuple
from datetime import datetime, timedelta
from exceptions import PhaseChangeException

from policy.abstract_policy import AbstractPolicy
from phase_intent_classifier_pb2 import IntentRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from task_manager_pb2 import TMRequest
from task_manager_pb2_grpc import TaskManagerStub
from taskmap_pb2 import Image, OutputInteraction, ScreenInteraction, Session, Task, Transcript
from database_pb2_grpc import DatabaseStub
from theme_pb2 import ThemeRequest, ThemeResults

from utils import (
    COOKING_FAREWELL,
    close_session,
    consume_intents,
    is_in_user_interaction,
    set_source,
    repeat_screen_response,
    RIND_FALLBACK_RESPONSE,
    logger,
    build_farewell_screen,
    DIY_FAREWELL,
    USER_OPTIONS_PROMPTS,
    STOP_SCREEN_PROMPTS
)


def populate_stop_screen(output):
    output.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
    output.screen.headline = "Goodbye!"
    image: Image = output.screen.image_list.add()
    image.path = "https://oat-2-data.s3.amazonaws.com/images/gifs/bye.gif"
    output.speech_text = random.choice(STOP_SCREEN_PROMPTS)
    output.screen.paragraphs.append("Hope to speak to you soon!")
    return output


def route_to_domain(session):
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["CancelIntent", "SearchIntent"])

    session.task_selection.preferences_elicited = False
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
    raise PhaseChangeException()


def route_to_execution(session: Session) -> None:
    """Redirect control of the response to the ExecutionPolicy.

    This method will simply reset ``session.task.phase`` to PLANNING and then
    raise a PhaseChangeException to cause the ExecutionPolicy to be activated.

    Args:
        session (Session): the current Session object

    Returns:
        Nothing, raises PhaseChangeException
    """
    session.task.phase = Task.TaskPhase.EXECUTING
    session.task.state.requirements_displayed = False
    session.task.state.validation_page = 0
    session.error_counter.no_match_counter = 0
    # session.turn[-1].user_request.interaction.intents.append("ChitChatIntent")
    raise PhaseChangeException()


class FarewellPolicy(AbstractPolicy):

    def __init__(self):
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        self.task_manager = TaskManagerStub(channel=channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)
        self.database = DatabaseStub(external_channel)

    @staticmethod
    def __stop_intent(session: Session) -> bool:
        """Check if a stop intent/utterance exists in the current turn.

        This checks for the existence of a StopIntent or the utterance
        being simply "stop". If either of these are found it returns 
        True, otherwise False.

        Args:
            session (Session): the current Session object

        Returns:
            bool: True if a stop intent/utterance found, False otherwise
        """
        last_interaction = session.turn[-1].user_request.interaction
        return "StopIntent" in last_interaction.intents or \
            "stop" == last_interaction.text.lower()

    def __set_transcript(self, session: Session, output: OutputInteraction) -> Tuple[Session, OutputInteraction]:
        """Populate the transcript field of an OutputInteraction.

        When a session is closed before the task is completed, this method is 
        called to populate the ``.transcript`` field of the OutputInteraction about
        to be returned to the client. The transcript is retrieved from the TaskManager
        service and consists of metadata about the TaskMap (title/rating/author)
        followed by a list of the steps in the task.

        Args:
            session (Session): the current Session object
            output (OutputInteraction): the OutputInteraction to populate
 
        Returns:
            tuple(updated Session, updated OutputInteraction)
        """
        request: TMRequest = TMRequest()
        request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
        request.state.ParseFromString(session.task.state.SerializeToString())
        # Populating Transcript when ending the interaction
        transcript: Transcript = self.task_manager.get_transcript(request)
        output.transcript.ParseFromString(transcript.SerializeToString())
        session.task.state.transcript_sent = True
        return session, output

    def __get_theme(self, session: Session) -> ThemeResults:

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

        current_theme = session.task_selection.theme.theme

        for date, theme in holiday_themes:
            if theme != current_theme and "day" in theme.lower():
                request.theme_word = theme
                return self.database.get_theme_by_id(request)

        request.theme_word = "Desserts"
        return self.database.get_theme_by_id(request)

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the FarewellPolicy class.

        This method will be called by PhasedPolicy if it encounters a Session
        with the ``.task.phase`` field set to Task.TaskPhase.CLOSING. This may
        happen if the user completes the task, but can also happen at any point
        during the interaction with the system if the user requests to stop.

        It will check if there is an active TaskMap and if the user did NOT
        request to end the interaction. In this case it indicates that the user
        has reached the end of the task, and a confirmation/congratulatory 
        response is constructed and returned.

        In all other cases the response returned is mostly empty, only populating
        the ``.transcript`` field of the OutputInteraction with a transcript of
        the current TaskMap. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, updated OutputInteraction)
        """

        if len(session.turn[-1].user_request.interaction.intents) == 0:
            intent_request = IntentRequest()
            intent_request.turns.append(session.turn[-1])

            output: OutputInteraction = OutputInteraction()
            intent_classification = self.phase_intent_classifier.classify_intent(intent_request)
            session.turn[-1].user_request.interaction.params.append(intent_classification.attributes.raw)

            translation_dict = {
                "select": "SelectIntent",
                "cancel": "CancelIntent",
                "restart": "CancelIntent",
                "search": "SearchIntent",
                "yes": "YesIntent",
                "no": "NoIntent",
                "repeat": "RepeatIntent",
                "confused": "ConfusedIntent",
                "show_more_results": "MoreResultsIntent",
                "show_requirements": "ShowRequirementsIntent",
                "show_more_details": "ConfusedIntent",
                "next": "NextIntent",
                "previous": "PreviousIntent",
                "stop": "StopIntent",
                "chit_chat": "ChitChatIntent",
                "ASR_error": "ASRErrorIntent",
                "answer_question": "QuestionIntent",
                "inform_capabilities": "InformIntent",
                "step_select": "ASRErrorIntent",
                "pause": 'PauseIntent',
                "start_task": 'StartTaskIntent',
                "set_timer": "createTimerIntent",
                "stop_timer": "deleteTimerIntent",
                "pause_timer": "pauseTimerIntent",
                "resume_timer": "resumeTimerIntent",
                "show_timers": "showTimerIntent",
            }

            # check if model output is in translation dict before updating session
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

        # Logic is that we want to ask if user as completed task if we don't have to stop abruptly
        output: OutputInteraction = OutputInteraction()
        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["CancelIntent"]):

            output = OutputInteraction()
            route_to_domain(session)
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["SearchIntent"]):
            output = OutputInteraction()
            route_to_domain(session)

        elif is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                    intents_list=["SearchIntent"]) and \
                is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                       intents_list=["YesIntent"]):
            # we failed to reroute to planning on the last farewell screen
            logger.info('We failed to reroute to planning on the last farewell screen, manually correcting...')
            session.turn[-1].user_request.interaction.MergeFrom(session.turn[-2].user_request.interaction)
            output = OutputInteraction()
            route_to_domain(session)

        # In this case we have reached the end of Execution
        if session.task.phase == Task.TaskPhase.CLOSING and \
                session.task.taskmap.title != '' and \
                not self.__stop_intent(session):
            # stuck in farewell
            if any([prompt in session.turn[-2].agent_response.interaction.speech_text for prompt in DIY_FAREWELL]) \
                    or any([prompt in session.turn[-2].agent_response.interaction.speech_text
                            for prompt in COOKING_FAREWELL]):
                output = OutputInteraction()
                # follow-up question/ system options
                output.speech_text = random.choice(USER_OPTIONS_PROMPTS)
            else:
                if session.domain == Session.Domain.COOKING:
                    output.speech_text = random.choice(COOKING_FAREWELL)
                else:
                    output.speech_text = random.choice(DIY_FAREWELL)

                session.task.phase = Task.TaskPhase.EXECUTING

            theme_result: ThemeResults = self.__get_theme(session)

            if not session.headless:
                session.task_selection.theme.Clear()
                screen = build_farewell_screen(theme_result=theme_result, session=session)
                output.screen.MergeFrom(screen)
                session.task.state.final_question_done = True
            else:
                output.speech_text += f" Try asking for {theme_result.theme_word} " \
                                      f"to check out more of our current recommendations! "

        else:
            session, output = self.__set_transcript(session, output)
            session, output = close_session(session, output)
            output = populate_stop_screen(output)

        set_source(output)
        return session, output
