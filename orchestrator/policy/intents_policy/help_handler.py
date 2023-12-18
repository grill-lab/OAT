import random
import grpc
import os

from datetime import datetime, timedelta
from typing import Tuple, List

from taskmap_pb2 import OutputInteraction, Session, Task
from theme_pb2 import ThemeResults, ThemeRequest
from database_pb2_grpc import DatabaseStub
from exceptions import PhaseChangeException

from utils import (
    repeat_screen_response, set_source, is_in_user_interaction, CHITCHAT_FALLBACK,
    get_helpful_prompt, build_help_grid_screen, logger, get_helpful_options,
)

from .abstract_intent_handler import AbstractIntentHandler


class HelpHandler(AbstractIntentHandler):

    def __init__(self):
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        self.database = DatabaseStub(external_channel)

    def __get_theme(self, session: Session) -> ThemeResults:

        request = ThemeRequest()

        relevant_dates = []
        now_date = datetime.today()
        for i in range(7):
            date = now_date + timedelta(days=i)
            relevant_dates.append(date.strftime("%d-%m-%Y"))

        # no current marketing event, so get themed holidays
        holiday_themes = []
        for date in relevant_dates:
            request.date = date
            theme = self.database.get_theme_by_date(request)
            if len(theme.queries) > 0:
                holiday_themes.extend([(date, theme_sug) for theme_sug in theme.queries])

        logger.info(f"Found date themes: {holiday_themes}")

        current_theme = session.task_selection.theme.theme

        for date, theme in holiday_themes:
            if theme != current_theme:
                request.theme_word = theme
                return self.database.get_theme_by_id(request)

        request.theme_word = "Desserts"
        return self.database.get_theme_by_id(request)

    @property
    def caught_intents(self) -> List[str]:
        """Defines the set of intents handled by this class.

        Returns:
            List[str]: list of intent names
        """
        return ["HelpIntent", "ConfusedIntent", "InformIntent"]

    @staticmethod
    def populate_help_response(help_words, help_keyword, help_response, session):
        output = OutputInteraction()
        logger.info(f'MATCHING HELP RESPONSE for keyword {help_keyword}: {help_response}')
        output.speech_text = help_response
        output = repeat_screen_response(session, output)
        output.screen.hint_text = help_keyword.split("_button")[0]
        session.task.state.help_corner_active = True

        session.turn[-1].user_request.interaction.text = help_keyword.split("_button")[0]

        exit_prompt = "If you want to exit the help corner, " \
                      "just click the back button in the top left corner or tell me what you " \
                      "would like to do. "
        if session.turn[-1].user_request.interaction.text == session.turn[-2].user_request.interaction.text or \
                (is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                        utterances_list=[p for p in help_words]) and
                 not exit_prompt in session.turn[-2].agent_response.interaction.speech_text):
            output.speech_text = f"{output.speech_text} {exit_prompt}"

        return output

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the HelpHandler class.

        This method should only be called when the IntentsPolicy is triggered for any of
        the intents returned by ``caught_intents``. It will construct and return a fixed 
        response designed to aid the user based on the current phase that the Session is in. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """

        phase = session.task.phase

        if session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:

            if "_button" in session.turn[-1].user_request.interaction.text and \
                    not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')

            logger.info('We are in help corner - ACTIVE')
            current_theme = None

            # we hit the theme button so need to call the theme db
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      utterances_list=['theme_button']):
                if phase == Task.TaskPhase.DOMAIN or phase == Task.TaskPhase.PLANNING:
                    current_theme = self.__get_theme(session)

                    help_options = get_helpful_options(session, current_theme)
                    help_words = list(help_options.keys())
                    logger.info(f'The current help options are: {help_words}')

                    if current_theme is not None:
                        help_keyword = session.turn[-1].user_request.interaction.text
                        help_response = help_options.get(help_keyword.split("_button")[0])
                        output = self.populate_help_response(help_words=help_words, help_keyword=help_keyword,
                                                             help_response=help_response, session=session)
                else:
                    current_theme = None

            if current_theme is None:
                # we don't need to get the themes from the theme db
                help_options = get_helpful_options(session, None)
                help_words = list(help_options.keys())
                logger.info(f'The current help options are: {help_words}')

                if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          utterances_list=[f'{p}_button' for p in help_words]):
                    help_keyword = session.turn[-1].user_request.interaction.text
                    help_response = help_options.get(help_keyword.split("_button")[0])
                    output = self.populate_help_response(help_words=help_words, help_keyword=help_keyword,
                                                         help_response=help_response, session=session)

                else:
                    logger.info('Rerouting due to no help options match')
                    session.task.state.help_corner_active = False
                    del session.turn[-1].user_request.interaction.intents[:]
                    raise PhaseChangeException()

        # we get rerouted from QA were we got a system capabilities question from QA classification,
        # and we have the screen available
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['Consumed.QuestionIntent', "InformIntent"],
                                    utterances_list=['what can you do', "what can i do"]) and not session.headless:
            output = build_help_grid_screen(session)
            session.task.state.help_corner_active = True
        
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['Consumed.ChitChatIntent']):
            # means we rerouted because the chitchat responses were rubbish.
            PREFIX = random.choice(CHITCHAT_FALLBACK)
            output = OutputInteraction()
            # hacky fix for domain/ planning phase:
            if phase == Task.TaskPhase.PLANNING and len(session.task_selection.candidates) == 0:
                phase = Task.TaskPhase.DOMAIN
            tutorial_list = get_helpful_prompt(phase=phase, task_title=session.task.taskmap.title,
                                                task_selection=session.task_selection, headless=session.headless)
            helpful_prompt = random.choice(tutorial_list)
            output.speech_text = f'{PREFIX}{helpful_prompt}'
            output = repeat_screen_response(session, output)

        # any other classified Confused Intent
        else:
            output = OutputInteraction()
            # hacky fix for domain/ planning phase:
            if phase == Task.TaskPhase.PLANNING and len(session.task_selection.candidates) == 0:
                phase = Task.TaskPhase.DOMAIN
            tutorial_list = get_helpful_prompt(phase=phase, task_title=session.task.taskmap.title,
                                               task_selection=session.task_selection, headless=session.headless)
            helpful_prompt = random.choice(tutorial_list)
            output.speech_text = f'{helpful_prompt}'
            if session.turn[-1].user_request.interaction.text == "":
                session.turn[-1].user_request.interaction.text = "help"
            output = repeat_screen_response(session, output)

        output.idle_timeout = 10

        if phase == Task.TaskPhase.EXECUTING:
            if not session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True
                output.screen.background = session.task.taskmap.thumbnail_url

        set_source(output)
        return session, output
