import os
import random
import grpc

from typing import Optional, Tuple
from datetime import datetime, timedelta

from database_pb2_grpc import DatabaseStub
from exceptions import PhaseChangeException
from policy.abstract_policy import AbstractPolicy
from searcher_pb2 import SearchQuery, SearchResults, CandidateList
from searcher_pb2_grpc import QueryBuilderStub, SearcherStub
from semantic_searcher_pb2 import SemanticQuery, ThemeMapping
from semantic_searcher_pb2_grpc import SemanticSearcherStub
from taskmap_pb2 import InputInteraction, OutputInteraction, Session, TaskmapCategoryUnion, Task
from theme_pb2 import ThemeRequest, ThemeResults

from utils import (
    display_screen_results,
    is_in_user_interaction,
    populate_choices,
    repeat_screen_response,
    set_source,
    logger,
    jaccard_sim
)


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

    def get_theme(self, search_utterance: str) -> str:
        """Check for theme matches using the SemanticSearcher.

        This method makes an RPC to the SemanticSearcher in neural_functionalities, passing
        it the current utterance. The theme field of the generated ``ThemeMapping`` is
        then returned as the result. 

        Args:
            search_utterance (str): most recent user utterance from current Session

        Returns:
            matched theme, if any (str)
        """
        semantic_query = SemanticQuery()
        semantic_query.text = search_utterance
        matched_theme: ThemeMapping = self.semantic_searcher.search_theme(semantic_query)

        if matched_theme.theme != "":
            relevant_dates = []
            now_date = datetime.today()
            for i in range(7):
                date = now_date + timedelta(days=i)
                relevant_dates.append(date.strftime("%d-%m-%Y"))

            request = ThemeRequest()
            request.theme_word = matched_theme.theme
            current_theme_results: ThemeResults = self.database.get_theme_by_id(request)

            if current_theme_results.date != "":
                theme_date = datetime.strptime(current_theme_results.date, "%d-%m-%Y")
                if now_date - timedelta(days=1) < theme_date <= now_date + timedelta(days=7):
                    return matched_theme.theme
                else:
                    logger.info(f"Best theme match {matched_theme.theme} is currently not active due to "
                                f"start date {current_theme_results.date}, skipping theme")
            else:
                return matched_theme.theme
        return ""

    def __get_theme_meta(self, theme: str) -> ThemeResults:
        """Searches for curated TaskMaps matching the given theme.

        Checks the theme database for curated TaskMaps matching the given theme
        and returns them through a ThemeResults object.

        Args:
            theme (str): a theme identifier

        Returns:
            a ThemeResults object
        """
        request = ThemeRequest()
        request.theme_word = theme
        theme_results: ThemeResults = self.database.get_theme_by_id(request)
        return theme_results

    def __augment_theme_results(self, session: Session, theme_results: ThemeResults) -> CandidateList:
        """Performs a normal search for taskmaps using the current utterance.

        This is used by the ``step`` method to append more TaskMaps to the curated set by
        running a standard search based on the current utterance.

        Args:
            session (Session): the current Session object

        Returns:
            a CategoryUnion List
        """

        if len(theme_results.popular_tasks) > 0:
            del session.task_selection.elicitation_utterances[:]
            session.task_selection.elicitation_utterances.append(random.choice(theme_results.popular_tasks))
        elif len(theme_results.results.candidates) < 3:
            session.task_selection.elicitation_utterances.append(
                session.turn[-1].user_request.interaction.text
            )
        else:
            theme_title = theme_results.description if theme_results.theme_word == "current_recommendation" \
                else theme_results.theme_word
            session.task_selection.elicitation_utterances.append(theme_title)

        query: SearchQuery = self.query_builder.synthesize_query(session)

        search_results: SearchResults = self.searcher.search_taskmap(query)
        candidate_list = search_results.candidate_list

        # only retrieve tasks, not categories
        candidate_list_filtered = []
        for candidate in candidate_list.candidates:
            if candidate.HasField('task'):
                candidate_list_filtered.append(candidate)

        del candidate_list.candidates[:]
        candidate_list.candidates.extend(candidate_list_filtered)

        return candidate_list

    def __check_new_search_param(self, user_interaction, theme) -> bool:
        if user_interaction.params:
            if user_interaction.params[0] == 'yes()':
                return False
            elif "select" in user_interaction.params[0]:
                return False

            theme_word = str(self.__get_theme_meta(theme).theme_word).lower()
            if user_interaction.text == theme_word.lower():
                return False

            new_search_param = user_interaction.params[0].split("(")[1].split(")")[0].strip("\"").lower()
            similarity = jaccard_sim(new_search_param, theme_word)

            # comparing NDP extracted params with theme word
            if similarity < 0.4 or new_search_param == "none":
                logger.info(f'NEW SEARCH due to SIM: {theme_word} <-> {new_search_param} with score {similarity}')
                return True

            # comparing user interaction with theme word
            similarity = jaccard_sim(user_interaction.text.lower(), theme_word)

            if similarity < 0.4:
                logger.info(f'NEW SEARCH due to SIM: {theme_word} <-> {user_interaction.text} with score {similarity}')
                return True

        return False

    @staticmethod
    def get_theme_title(current_theme: ThemeResults):
        return current_theme.description \
            if current_theme.theme_word == "current_recommendation" else current_theme.theme_word

    def step(self, session: Session) -> Tuple[Optional[Session], Optional[OutputInteraction]]:
        """Step method for the ThemePolicy class.

        If this method is triggered, it should indicate that a theme has been detected in the
        current Session and that some curated TaskMaps are in the theme database. 

        If the current utterance is classed as a ChitChatIntent, it will return a "trivia" response.
        If a SearchIntent is found instead, it will retrieve curated TaskMaps from the theme database,
        augmenting them with TaskMaps returned by a standard search using the current utterance.

        If either of these cases are triggered, the policy will return an updated Session and 
        OutputInteraction. 

        If neither are triggered, it will return a (None, None) tuple to indicate no theme response
        was possible. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction) or tuple(None, None)
        """
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
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=user_interaction, intents_list=["SearchIntent"]):

            if self.__check_new_search_param(user_interaction, theme):
                logger.info('NEW SEARCH IN THEMES!!!!')
                session.task_selection.preferences_elicited = False
                session.task_selection.elicitation_turns = 0
                session.task_selection.results_page = 0
                session.domain = Session.Domain.UNKNOWN
                del session.task_selection.elicitation_utterances[:]
                session.task_selection.theme.Clear()
                session.task.taskmap.Clear()
                session.task.state.Clear()
                session.task.phase = Task.TaskPhase.DOMAIN
                session.domain = 0
                session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                raise PhaseChangeException()
            else:
                session.task_selection.results_page = 0
                theme_results = self.__get_theme_meta(theme)
                curated_taskmap_list = theme_results.results
                curated_candidate_list = CandidateList()
                for taskmap in curated_taskmap_list.candidates:
                    union = TaskmapCategoryUnion()
                    union.task.CopyFrom(taskmap)
                    curated_candidate_list.candidates.append(union)

                # only need to augment the candidates if we have less than 9
                if len(curated_candidate_list.candidates) < 9:
                    # augmenting the curated list
                    augmented_taskmap_list = self.__augment_theme_results(session, theme_results)
                    curated_candidate_list.candidates.extend(augmented_taskmap_list.candidates)

                say_normal_introduction = True

                if len(curated_candidate_list.candidates) > 0:
                    first_cand = curated_candidate_list.candidates[0].task
                    if first_cand.dataset == "theme_finals" and theme_results.description != "":
                        say_normal_introduction = False

                if say_normal_introduction:
                    if not session.task_selection.theme_description_given:
                        excited_prompts = ["awesome", "excellent", "good call", "hurray", "well done", "woo hoo"]
                        speech_con = random.choice(excited_prompts)

                        theme_title = self.get_theme_title(current_theme=theme_results)
                        output.speech_text = f"You selected our {theme_title} theme. {speech_con}! "
                    else:
                        theme_title = self.get_theme_title(current_theme=theme_results)
                        returning_user = [f"Here are our {theme_title} recommendations. ",
                                          f"For {theme_title}, our recommendations are as follows: ",
                                          f"What do you think about our {theme_title} recommendations? "]
                        output.speech_text = random.choice(returning_user)

                    if not session.task_selection.theme_description_given and theme_results.description != "":
                        output.speech_text += theme_results.description + " "
                        session.task_selection.theme_description_given = True

                    if theme_results.description == "" and not session.task_selection.theme_description_given:
                        theme_responses: list = [
                            f"I have three great recommendations for '{session.task_selection.theme.theme}'. ",
                            f"Well, for  '{session.task_selection.theme.theme}', you can try one of my three "
                            f"all-time favorites.  "
                        ]
                        output.speech_text += " " + random.choice(theme_responses)
                    output.speech_text += populate_choices(curated_candidate_list.candidates)

                    if theme_results.description != "":
                        QUESTIONS = [" Which one would you like? ", " Which one do you prefer? ",
                                     " Which one would you like to do? "]
                        output.speech_text += random.choice(QUESTIONS)
                else:
                    # finals code
                    output.speech_text = ". ".join(theme_results.description.split(". ")[:-1]) + ". "
                    for idx, cand in enumerate(curated_candidate_list.candidates):
                        if cand.HasField("task"):
                            if cand.task.domain_name == "ai_generated":
                                if "(AI generated)" in theme_results.description:
                                    output.speech_text = output.speech_text.replace("(AI generated)", "")

                    QUESTIONS = [" Which one would you like? ", " Which one do you prefer? ",
                                 " Which one would you like to do? "]
                    output.speech_text += random.choice(QUESTIONS)

                # add results to session
                del session.task_selection.candidates_union[:]
                for candidate in curated_candidate_list.candidates:
                    new_c = session.task_selection.candidates_union.add()
                    new_c.ParseFromString(candidate.SerializeToString())

                # show results on screen
                if not session.headless:
                    on_click_list = display_screen_results(
                        curated_candidate_list.candidates[:3],
                        output, session.domain
                    )
                    output.screen.on_click_list.extend(on_click_list)
                    output.screen.headline = f"Theme: {session.task_selection.theme.theme}"

                if len(curated_candidate_list.candidates) > 0:
                    first = curated_candidate_list.candidates[0]
                    if not any(x == first for x in curated_candidate_list.candidates):
                        REPROMPTS.append(
                            f"{random.choice(curated_candidate_list.candidates).title} please")

                output.screen.hint_text = random.sample(REPROMPTS, 1)[0]
                set_source(output)
                return session, output

        return None, None
