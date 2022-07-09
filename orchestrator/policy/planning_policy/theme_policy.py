from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import (
    Session,
    Task,
    OutputInteraction,
    InputInteraction,
    ScreenInteraction,
    TaskMap,
    Image
)
from utils import (
    repeat_screen_response,
    is_in_user_interaction,
    consume_intents,
    close_session,
    logger,
    format_author,
    display_screen_results,
    populate_choices
)
import grpc
import os
import random
from exceptions import PhaseChangeException
from theme_pb2 import ThemeRequest, ThemeResults
from database_pb2_grpc import DatabaseStub
from semantic_searcher_pb2 import ThemeDocument, SemanticQuery, ThemeMapping
from semantic_searcher_pb2_grpc import SemanticSearcherStub
from searcher_pb2 import SearchQuery, TaskMapList
from searcher_pb2_grpc import SearcherStub,  QueryBuilderStub


class ThemePolicy(AbstractPolicy):
    """
    Policy to handle theme interactions. If here, session contains a theme
    """

    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])

        self.semantic_searcher = SemanticSearcherStub(neural_channel)
        self.database = DatabaseStub(external_channel)
        self.searcher = SearcherStub(channel)
        self.query_builder = QueryBuilderStub(channel)

    def get_theme(self, user_interaction: InputInteraction) -> str:
        semantic_query = SemanticQuery()
        semantic_query.text = user_interaction.text
        matched_theme: ThemeMapping = self.semantic_searcher.search_theme(semantic_query)

        return matched_theme.theme

    def __get_theme_meta(self, theme: str) -> ThemeResults:
        request = ThemeRequest()
        request.theme_word = theme
        theme_results: ThemeResults = self.database.get_theme_results(request)
        return theme_results
    
    def __augment_theme_results(self, session) -> TaskMapList:
        session.task_selection.elicitation_utterances.append(
            session.turn[-1].user_request.interaction.text
        )
        query: SearchQuery = self.query_builder.synthesize_query(session)
        search_results = self.searcher.search_taskmap(query)
        taskmap_list = search_results.taskmap_list

        return taskmap_list

    def step(self, session: Session) -> (Session, OutputInteraction):

        theme: str = session.task_selection.theme.theme
        output = OutputInteraction()
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction
        REPROMPTS = ["restart", "the first one"]
        
        if is_in_user_interaction(user_interaction=user_interaction, intents_list=["ChitChatIntent"],
                                  utterances_list=["tell me more", "Tell me more"]):

            theme_results = self.__get_theme_meta(theme)

            random_trivia = random.choice(theme_results.trivia)
            output.speech_text = random_trivia
            output.speech_text += " So, tell me. Which of these options do you want to try? "

            output = repeat_screen_response(session, output)
            output.screen.hint_text = random.sample(REPROMPTS, 1)[0]
            return session, output

        elif is_in_user_interaction(user_interaction=user_interaction, intents_list=["SearchIntent"]):
            session.task_selection.results_page = 0
            theme_results = self.__get_theme_meta(theme)
            curated_taskmap_list = theme_results.results

            # augmenting the curated list
            augmented_taskmap_list = self.__augment_theme_results(session)
            curated_taskmap_list.candidates.extend(augmented_taskmap_list.candidates)            

            # session.task_selection.elicitation_utterances.append(user_interaction.text)
            if not session.task_selection.theme_description_given and theme_results.description != "":
                output.speech_text = theme_results.description
                session.task_selection.theme_description_given = True

            if theme_results.description == "":
                theme_responses: list = [
                    f"I have three great recommendations for '{session.task_selection.theme.theme}'. ",
                    f"Well, for  '{session.task_selection.theme.theme}', you can try one of my three all-time favorites.  "
                ]
                output.speech_text += " " + random.choice(theme_responses)
            else:
                output.speech_text += " By the way. What do you think of these options? "
            output.speech_text += populate_choices(curated_taskmap_list.candidates)

            # add results to session
            del session.task_selection.candidates[:]
            for candidate in curated_taskmap_list.candidates:
                new_c = session.task_selection.candidates.add()
                new_c.ParseFromString(candidate.SerializeToString())

            # show results on screen
            if not session.headless:
                on_click_list = display_screen_results(
                    curated_taskmap_list.candidates[:3],
                    output
                )
                output.screen.on_click_list.extend(on_click_list)
                output.screen.background = 'https://grill-bot-data.s3.amazonaws.com/images/multi_domain_default.jpg'

            if len(curated_taskmap_list.candidates) > 0:
                first = curated_taskmap_list.candidates[0]
                if not any(x == first for x in curated_taskmap_list.candidates):
                    REPROMPTS.append(
                        f"{random.choice(curated_taskmap_list.candidates).title} please")

            output.screen.hint_text = random.sample(REPROMPTS, 1)[0]
            return session, output

        return None, None

