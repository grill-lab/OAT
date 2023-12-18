import grpc
import os
import random

from datetime import datetime
from database_pb2_grpc import DatabaseStub
from searcher_pb2_grpc import QueryBuilderStub, SearcherStub
from semantic_searcher_pb2_grpc import SemanticSearcherStub
from theme_pb2 import ThemeResults
from utils import (
    logger, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN,
    SUGGESTED_THEME_WEEK_with_examples
)


class ThemeSuggestion:
    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])

        self.semantic_searcher = SemanticSearcherStub(neural_channel)
        self.database = DatabaseStub(external_channel)
        self.searcher = SearcherStub(channel)
        self.query_builder = QueryBuilderStub(channel)

    @staticmethod
    def __get_current_theme_meta() -> ThemeResults:
        """Searches for curated TaskMaps matching the given theme.

        Checks the theme database for curated TaskMaps matching the given theme
        and returns them through a ThemeResults object.

        Returns:
            a ThemeResults object
        """
        # relevant_dates = []
        # now_date = datetime.today()
        # for i in range(7):
        #     date = now_date + timedelta(days=i)
        #     relevant_dates.append(date.strftime("%d-%m-%Y"))
        #
        # # check if we have a fixed current_recommendation
        # # if it has a date then we should only recommend it if it is in the date range T-7
        # request = ThemeRequest()
        # request.theme_word = "current_recommendation"
        # current_theme_results: ThemeResults = self.database.get_theme_by_id(request)
        #
        # if current_theme_results.date != "":
        #     theme_date = datetime.strptime(current_theme_results.date, "%d-%m-%Y")
        #     if now_date - timedelta(days=1) < theme_date <= now_date + timedelta(days=7):
        #         # relevant marketing theme
        #         return current_theme_results
        # else:
        #     logger.info('Current theme does not have a date')
        #
        # # no current marketing event, so get themed holidays
        # holiday_themes = []
        # for date in relevant_dates:
        #     request.date = date
        #     theme = self.database.get_theme_by_date(request)
        #     if len(theme.queries) > 0:
        #         holiday_themes.extend([(date, theme_sug) for theme_sug in theme.queries])
        #         break   # break here to save 0.6 seconds, only retrieve closest holiday theme
        #
        # logger.info(f"Found date themes: {holiday_themes}")
        #
        # if len(holiday_themes) > 0:
        #     request.theme_word = holiday_themes[0][1]
        #     return self.database.get_theme_by_id(request)

        return ThemeResults()

    def get_current_theme(self) -> ThemeResults:
        return self.__get_current_theme_meta()

    @staticmethod
    def build_current_recommendation_prompt(current_theme: ThemeResults) -> str:
        logger.info(f'Building theme prompt: {current_theme.theme_word}')
        logger.info(f'Building theme prompt: {current_theme.description}')
        logger.info(f'{current_theme.intro_sentence}')
        logger.info(f'{current_theme.alternative_description}')

        theme_title = current_theme.description \
            if current_theme.theme_word == "current_recommendation" else current_theme.theme_word

        if current_theme.intro_sentence is not None:
            prompts = SUGGESTED_THEME_WEEK_with_examples
            alternative_description = current_theme.alternative_description \
                if current_theme.alternative_description != "" else theme_title
            speech_text = random.choice(prompts).format(theme_title, current_theme.intro_sentence,
                                                        alternative_description)
        else:
            # actually including 'Week' in this prompt
            prompts = SUGGESTED_THEME_WEEK
            speech_text = random.choice(prompts).format(theme_title)

        return speech_text

    @staticmethod
    def get_theme_title(current_theme: ThemeResults):
        return current_theme.description \
            if current_theme.theme_word == "current_recommendation" else current_theme.theme_word

    @staticmethod
    def get_subcaption(current_theme: ThemeResults):
        theme_title = current_theme.description \
            if current_theme.theme_word == "current_recommendation" else current_theme.theme_word

        # if there is no theme today, we fall back to the default choices
        if current_theme.theme_word == "":
            return "Theme of the Day"

        # it is National XYZ day today
        if current_theme.date == datetime.today().strftime("%d-%m-%Y") and \
                current_theme.theme_word != "current_recommendation":
            return 'Theme of the Day'

        # it is National XYZ within the next 7 days
        else:
            return 'Theme of the Week'

    def build_theme_intro_prompt(self, current_theme: ThemeResults):
        theme_title = current_theme.description \
            if current_theme.theme_word == "current_recommendation" else current_theme.theme_word

        # it is National XYZ day today
        if current_theme.date == datetime.today().strftime("%d-%m-%Y") and \
                current_theme.theme_word != "current_recommendation":
            prompts = SUGGESTED_THEME_DAY
            speech_text = random.choice(prompts).format(theme_title)

        # it is National XYZ within the next 7 days
        elif "Day" in theme_title:
            theme_date = datetime.strptime(current_theme.date, "%d-%m-%Y")
            now_date = datetime.today()
            days = theme_date - now_date
            prompts = SUGGESTED_THEME_DAY_COUNTDOWN
            speech_text = random.choice(prompts).format(theme_title,f'{str(days.days + 1)} day{"s" if days.days + 1 > 1 else ""}')
        else:
            # specific recommendation time! E.g. Baking week and summer
            speech_text = self.build_current_recommendation_prompt(current_theme)
        return speech_text
