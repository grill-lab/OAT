import random
import grpc
import os

from compiled_protobufs.taskmap_pb2 import ScreenInteraction, Image, OutputInteraction
from compiled_protobufs.theme_pb2 import ThemeResults, ThemeRequest
from compiled_protobufs.semantic_searcher_pb2_grpc import SemanticSearcherStub
from compiled_protobufs.database_pb2_grpc import DatabaseStub

from utils import logger


class HandCraftedHome:

    def __init__(self) -> None:
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])

        self.semantic_searcher = SemanticSearcherStub(neural_channel)
        self.database = DatabaseStub(external_channel)

    def __retrieve_theme(self, theme_word) -> ThemeResults:
        request = ThemeRequest()
        request.theme_word = theme_word
        current_theme_results: ThemeResults = self.database.get_theme_by_id(request)
        if current_theme_results.theme_word != "":
            logger.info(f'Theme found: {current_theme_results.theme_word}')
        return current_theme_results

    def populate_custom_screen(self, screen: ScreenInteraction, current_theme: ThemeResults) -> OutputInteraction:
        """Populate a ScreenInteraction with default choices when domain is not recognised.

        Args:
            screen (ScreenInteraction): the ScreenInteraction from the current OutputInteraction
            current_theme: ThemeResults

        Returns:
            updated ScreenInteraction
        """

        screen.headline = "Hi, I'm TaskBot!"

        screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

        PROMPTS = ["what can you do"]

        output = OutputInteraction()

        base_theme = self.__retrieve_theme(current_theme.description)

        if base_theme.description != "":
            output.speech_text = f'{base_theme.description} '

        ordinal_phrases = [
            ["The first one is", "The second is", "And, finally"],
            ["First is", "Second is", "And, third"]
        ]
        ordinals = random.choice(ordinal_phrases)

        for idx, option in enumerate(current_theme.popular_tasks):
            theme_result = self.__retrieve_theme(option)
            logger.info(theme_result.theme_word)

            tile: Image = screen.image_list.add()
            if len(theme_result.results.candidates) > 0:
                tile.path = theme_result.results.candidates[0].thumbnail_url

            tile.title = theme_result.theme_word
            tile.description = theme_result.description
            screen.on_click_list.append(theme_result.theme_word)
            PROMPTS.append(theme_result.theme_word)
            if base_theme.description == "":
                output.speech_text += f"{ordinals[idx]} {theme_result.theme_word}. "

        screen.hint_text = random.sample(PROMPTS, 1)[0]
        output.screen.MergeFrom(screen)

        return output
