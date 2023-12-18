import os
import random
import grpc

from typing import Tuple, Optional

from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import (
    InputInteraction, OutputInteraction, Session, ScreenInteraction, Image, TaskmapCategoryUnion, Task
)
from searcher_pb2_grpc import QueryBuilderStub, SearcherStub
from searcher_pb2 import SearchQuery, CandidateList, TaskMapList, SearchResults, TaskmapIDs

from offline_pb2 import SubCategory
from exceptions import PhaseChangeException

from utils import (
    close_session,
    is_in_user_interaction,
    logger,
    set_source,
    INTRODUCE_CATEGORY,
    repeat_screen_response,
    CATEGORY_RESULTS_READING,
    NO_MORE_RESULTS,
    CATEGORY_RESULTS,
)


class CategoryPolicy(AbstractPolicy):

    def __init__(self):

        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])

        self.searcher = SearcherStub(channel)
        self.query_builder = QueryBuilderStub(channel)

        with open('/source/policy/planning_policy/data/bad_category_task_urls.txt', 'r') as f:
            lines = f.readlines()
            self.bad_urls = {line.rstrip().lower() for line in lines}

    @staticmethod
    def populate_screen(output, candidates):
        output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL
        on_click_list = []
        for idx, candidate in enumerate(candidates):
            image: Image = output.screen.image_list.add()
            image.path = candidate['image_url']
            image.title = candidate['title']
            on_click_list.append(str(idx + 1))

        return on_click_list, output

    def __search_similar_tasks(self, session, new_query) -> TaskMapList:
        """Performs a normal search for taskmaps using the current utterance.

        This is used by the ``step`` method to append more TaskMaps to the curated set by
        running a standard search based on the current utterance.

        Args:
            session (Session): the current Session object
            new_query (String): a query consisting of the title of the category and subcategory
        Returns:
            a TaskMapList
        """
        query: SearchQuery = self.query_builder.synthesize_query(session)
        query.last_utterance = new_query
        search_results = self.searcher.search_taskmap(query)

        taskmap_list = TaskMapList()

        for candidate in search_results.candidate_list.candidates:
            if candidate.HasField('task'):
                taskmap_list.candidates.append(candidate.task)

        return taskmap_list

    def process_options_sub_categories(self, sub_category: SubCategory, session, select_option: int) -> CandidateList:

        """
        Function to retrieve the taskmaps for the pre-defined queries in the sub-category
        Args:
            - SubCategory: selected sub category in the previous turn
            - Session: holding all session information
            - select_option: determines the subcategories index the user selected
        Returns:
            - CandidateList: a list of taskmaps which are converted to the list of candidate options to select from
        """

        del session.task_selection.candidates_union[:]
        session.task_selection.elicitation_utterances.append(sub_category.title)

        task_ids = [task.taskmap_id for task in
                    session.task_selection.category.sub_categories[select_option].candidates
                    if task.url not in self.bad_urls]

        ids = TaskmapIDs()
        ids.ids.extend(task_ids)

        search_results: SearchResults = self.searcher.retrieve_taskmap(ids)

        found_ids = set()
        for c in search_results.candidate_list.candidates:
            found_ids.add(c.task.taskmap_id)

        for candidate in search_results.candidate_list.candidates[:3]:
            new_c = session.task_selection.candidates_union.add()
            new_c.MergeFrom(candidate)

        if len(session.task_selection.candidates_union) < 3:
            new_query = session.task_selection.category.title + ' and ' + sub_category.title + ' ' + sub_category.title
            results = self.__search_similar_tasks(session, new_query).candidates
            task_rank = 0
            while len(session.task_selection.candidates_union) < 3:
                # __search_similar_tasks can occasionally return fewer results than
                # expected here, so have to check if task_rank is a valid index
                if task_rank >= len(results):
                    logger.warning(f'Not enough results to fill task candidates (only have {len(session.task_selection.candidates_union)}/3)')
                    break
                new_c = session.task_selection.candidates_union.add()
                new_c.task.MergeFrom(results[task_rank])
                task_rank += 1

        return session.task_selection.candidates_union

    def get_agent_response(self, session: Session, user_interaction: InputInteraction):

        if session.task_selection.category.title == "":
            logger.info("CATEGORY TITLE MISSING")
            return None, None, None

        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['SelectIntent', 'Consumed.PreviousIntent']):

            if is_in_user_interaction(user_interaction=user_interaction,
                                      intents_list=['Consumed.PreviousIntent']):
                intent_idx = -2
                select_intents_count = 0
                while select_intents_count < 2:
                    if "SelectIntent" in session.turn[intent_idx].user_request.interaction.intents:
                        select_intents_count += 1
                    intent_idx -= 1
                user_choice = session.turn[intent_idx + 1].user_request.interaction
            else:
                user_choice = session.turn[-1].user_request.interaction

            if session.task_selection.preferences_elicited or session.task_selection.categories_elicited == 3:
                params = "1"
            else:
                try:
                    session.task_selection.elicitation_utterances.append(user_choice.params[0].split("select(")[1][:-1])
                    params = user_choice.params[0].split("select(")[1][:-1]
                except:
                    params = "1"

            if session.task_selection.categories_elicited >= 1:
                try:
                    selected_category_idx = int(params) - 1
                    selected_category = session.task_selection.category.sub_categories[selected_category_idx]

                    if session.task_selection.preferences_elicited:
                        speech_category_selected = session.task_selection.category.title
                        session.task_selection.preferences_elicited = False
                        session.task_selection.categories_elicited = 3  # distinguish skipping mid-layer (should have the same behavior as when it is set to == 2)
                    else:
                        speech_category_selected = selected_category.title
                        session.task_selection.categories_elicited = 2

                    speech_text = random.choice(CATEGORY_RESULTS).format(speech_category_selected)
                    headline_text = session.task_selection.category.title + ' / ' + selected_category.title

                except Exception as e:
                    logger.info("ValueError")
                    logger.info(e)
                    logger.info(session.turn[-1].user_request.interaction)
                    selected_category_idx = 0
                    selected_category = session.task_selection.category.sub_categories[selected_category_idx]
                    speech_text = f"How about {selected_category.title}? "
                    headline_text = session.task_selection.category.title + ' / ' + selected_category.title

                candidates = self.process_options_sub_categories(selected_category, session, selected_category_idx)
                speech_text += self.__populate_category_choices([candidate.task.title for candidate in candidates])

                if not candidates:
                    # choosing the first as default
                    logger.info(
                        f'Choosing first category as default: {session.task_selection.category.sub_categories[0].title}')
                    options = session.task_selection.category.sub_categories[0]
                    candidates = self.process_options_sub_categories(options, session)
                    speech_text += self.__populate_category_choices([candidate.task.title for candidate in candidates])
                    headline_text = session.task_selection.category.title + ' / ' + \
                                    session.task_selection.category.sub_categories[0].title
                return speech_text, candidates, headline_text

            else:
                return None, None, None

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['ThemeSearchIntent']):

            logger.info("IN THEME SEARCH")

            sub_tree = ""
            # if session.task_selection.category.description:
            #     sub_tree = f"{session.task_selection.category.description}. " # enable when descriptions are approved

            candidates = [c.title for c in session.task_selection.category.sub_categories]
            sub_tree += random.choice(INTRODUCE_CATEGORY).format(session.task_selection.category.title, candidates[0],
                                                                 candidates[1], candidates[2])
            headline_text = session.task_selection.category.title
            session.task_selection.categories_elicited = 1
            if len(session.task_selection.elicitation_utterances) > 2:
                del session.task_selection.elicitation_utterances[-2:]

            return sub_tree, session.task_selection.category.sub_categories, headline_text

        else:
            logger.info('not defined behaviour for other intents than ThemeSearch or Select')
            return None, None, None

    @staticmethod
    def __populate_category_choices(candidates) -> str:
        speech_text = ''
        idx: int
        ordinal_phrases = [
            ["The first one is", "The second is", "And, finally"],
            ["First is", "Second is", "And, third"]
        ]
        ordinals = random.choice(ordinal_phrases)
        for idx, candidate in enumerate(candidates[:3]):
            result = f"{candidate}"
            speech_text += f'{ordinals[idx]}: {result}. '
        return speech_text

    def step(self, session: Session) -> Tuple[Optional[Session], Optional[OutputInteraction]]:

        output = OutputInteraction()
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction

        # when user comes from elicitation -> skip middle layer in categories by redirecting to SelectIntent
        if session.task_selection.preferences_elicited:
            session.turn[-1].user_request.interaction.intents.append("SelectIntent")
            session.task_selection.categories_elicited = 1

        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['DangerousQueryIntent']):

            output.speech_text = "I’m sorry, I can’t help with this type of task."
            session.task_selection.categories_elicited = 0
            session, output = close_session(session, output)

            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=["RepeatIntent"]):

            try:
                last_non_helper_response = -2
                while session.turn[last_non_helper_response].agent_response.interaction.source.policy == "help_handler":
                    last_non_helper_response -= 1
                output.speech_text = session.turn[last_non_helper_response].agent_response.interaction.speech_text
            except:
                output.speech_text = session.turn[-2].agent_response.interaction.speech_text

            if last_non_helper_response == -2:
                output = repeat_screen_response(session, output)
                set_source(output)
                return session, output

            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.extend(
                session.turn[last_non_helper_response].user_request.interaction.intents)

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=["MoreResultsIntent"]):
            output = repeat_screen_response(session, output)
            prev_response = session.turn[-2].agent_response.interaction.speech_text

            split_texts = [prev_response.split(listing_selection_begin) for listing_selection_begin in
                           CATEGORY_RESULTS_READING]

            output_read_results = ""
            for split_text in split_texts:
                if len(split_text) > 1:
                    output_read_results = split_text[1]
            if output_read_results == "":
                logger.warning("Did not read results!")

            output.speech_text = random.choice(NO_MORE_RESULTS) + output_read_results

            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=["PreviousIntent"]):

            if session.task_selection.categories_elicited == 2:
                # redirect from displaying taskmaps to displaying subcategories
                session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                del session.task_selection.candidates_union[:]
                session.task_selection.categories_elicited -= 1

            elif session.task_selection.categories_elicited == 1:
                # start a new search with the original query
                del session.task_selection.candidates_union[:]
                session.task_selection.results_page = 0
                session.task_selection.category.Clear()
                original_query = session.task_selection.elicitation_utterances[0]
                del session.task_selection.elicitation_utterances[:]
                del session.turn[-1].user_request.interaction.intents[:]
                session.task_selection.categories_elicited -= 1
                session.task_selection.elicitation_utterances.append(original_query)
                session.turn[-1].user_request.interaction.text = original_query
                session.turn[-1].user_request.interaction.intents.append("SpecificSearchIntent")
                return session, output

            elif session.task_selection.categories_elicited == 3:
                session.task_selection.categories_elicited = 0
                session.task_selection.results_page = 0
                del session.task_selection.candidates_union[:]
                session.task_selection.category.Clear()
                del session.task_selection.elicitation_utterances[:]
                del session.turn[-1].user_request.interaction.intents[:]
                session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                session.task.phase = Task.TaskPhase.DOMAIN
                raise PhaseChangeException()

            else:
                logger.warning("SHOULD NOT BE HERE")

        if session.task_selection.category.title == "":
            session.task_selection.preferences_elicited = True
            logger.info('leaving category elicitation because no category')
            session.task.state.help_corner_active = False
            session.task_selection.elicitation_turns = 0
            session.task_selection.results_page = 0
            session.task_selection.categories_elicited = 0
            session.domain = Session.Domain.UNKNOWN
            del session.task_selection.elicitation_utterances[:]
            session.task_selection.theme.Clear()
            session.task_selection.category.Clear()
            del session.task_selection.candidates_union[:]
            session.task.phase = Task.TaskPhase.DOMAIN
            raise PhaseChangeException()

        speech_text, candidates, headline_text = self.get_agent_response(session, user_interaction)

        if candidates:
            output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL
            on_click_list = []
            for idx, candidate in enumerate(candidates[:3]):
                image: Image = output.screen.image_list.add()
                if str(type(candidate)) == str(TaskmapCategoryUnion):
                    if candidate.HasField('task'):
                        image.path = candidate.task.thumbnail_url
                        image.title = candidate.task.title
                        image.alt_text = f'({random.randint(5, 19)})'
                        candidate.task.rating_out_100 = random.randint(80, 100)
                        image.ratingValue = candidate.task.rating_out_100
                    else:
                        image.path = candidate.category.sub_categories[0].thumbnail_url
                        image.title = candidate.category.title
                elif str(type(candidate)) == str(SubCategory):
                    image.path = candidate.candidates[0].image_url
                    image.title = candidate.title
                else:
                    logger.warning(f"SELECTED NEITHER A CATEGORY NOR A SUBCATEGORY - {type(candidate)}")
                    image.path = candidate.candidates[0].image_url

                on_click_list.append(str(idx + 1))

            output.screen.headline = f'CATEGORY: {headline_text}'
            output.screen.on_click_list.extend(on_click_list)
            output.speech_text = speech_text

        else:
            session.task_selection.preferences_elicited = True
            logger.info('leaving category elicitation because no candidates')
            session.task.state.help_corner_active = False
            session.task_selection.elicitation_turns = 0
            session.task_selection.results_page = 0
            session.task_selection.categories_elicited = 0
            session.domain = Session.Domain.UNKNOWN
            del session.task_selection.elicitation_utterances[:]
            session.task_selection.theme.Clear()
            session.task_selection.category.Clear()
            del session.task_selection.candidates_union[:]
            session.task.phase = Task.TaskPhase.DOMAIN
            raise PhaseChangeException()

        set_source(output)
        return session, output
