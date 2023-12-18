import os
import random
import grpc

from typing import Tuple

from dangerous_task_pb2_grpc import DangerousStub
from database_pb2_grpc import DatabaseStub
from exceptions import PhaseChangeException
from phase_intent_classifier_pb2 import IntentRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from policy.abstract_policy import AbstractPolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from policy.chitchat_policy import DefaultPolicy as DefaultChitChatPolicy
from .elicitation_policy import ElicitationPolicy
from .category_policy import CategoryPolicy
from .theme_policy import ThemePolicy

from searcher_pb2 import SearchQuery, CandidateList, UserUtterance, ProcessedString
from searcher_pb2_grpc import QueryBuilderStub, SearcherStub
from taskmap_pb2 import OutputInteraction, Session, Task, TaskmapCategoryUnion
from utils import (
    ALL_RESULTS_PROMPT,
    ASR_ERROR,
    DANGEROUS_TASK_RESPONSES,
    FIRST_RESULT_SET_PROMPT,
    MORE_RESULTS_INTRO,
    OUT_OF_RANGE_COREF_RESPONSE,
    PREVIOUS_RESULTS_INTRO,
    RIND_FALLBACK_RESPONSE,
    SELECT_POSSIBILITY,
    YES_PLANNING,
    close_session,
    consume_intents,
    display_screen_results,
    headless_task_summary,
    PAUSING_PROMPTS,
    is_in_user_interaction,
    logger,
    populate_choices,
    repeat_screen_response,
    screen_summary_taskmap,
    set_source,
    build_chat_screen,
    INGREDIENT_FUNNY_REMARK,
    should_trigger_theme
)


def route_to_domain(session: Session) -> None:
    """Redirect control of the response to the DomainPolicy class.

    This method is typically triggered in response to a negative intent from the
    user (CancelIntent/NoIntent). It will consume any CancelIntent in the current
    InputInteraction, update some state in the Session, and set ``session.domain``
    and ``session.task.phase`` to their original states in order to trigger the
    DomainPolicy again.

    Args:
        session (Session): the current Session object

    Returns:
        Nothing, raises PhaseChangeException
    """
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["CancelIntent"])

    session.task_selection.preferences_elicited = False
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


class PlannerPolicyV2(AbstractPolicy):

    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])

        self.searcher = SearcherStub(channel)
        self.query_builder = QueryBuilderStub(channel)
        self.dangerous_task_filter = DangerousStub(external_channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)

        self.database = DatabaseStub(external_channel)

        self.theme_policy = ThemePolicy()
        self.qa_policy = DefaultQAPolicy()
        self.elicitation_policy = ElicitationPolicy()
        self.category_policy = CategoryPolicy()
        self.chitchat_policy = DefaultChitChatPolicy()

    def __search_intent_builder(self, query: str) -> str:
        """Given the current utterance, decide which type of SearchIntent it represents.

        This method filters out all words from the utterance that appear in either the
        local ``vague_words`` list or the indri stopwords list, stored locally as
        shared/utils/indri_stop_words.txt.

        If there are no words remaining in the query after removing stopwords, the utterance
        is classed as a "VagueSearchIntent". If there are any remaining words, it's instead
        classed as a "SpecificSearchIntent".

        Args:
            query (str): the most recent user utterance

        Returns:
            either "SpecificSearchIntent" or "VagueSearchIntent"
        """
        # Find specific words by removing stopwords.
        elicitation_vague_words = [
            'build', 'bake', 'quick', 'home', 'improvement', 'home improvement', 'fix', 'eat', 'search',
            "task", "recommend", "prefer", "different", "cook", "diy", "cooking", 'improv', 'favorit'
        ]

        user_utterance = UserUtterance()
        user_utterance.text = query

        # stem the word with pyserini
        processed_str: ProcessedString = self.query_builder.processing_utterance(user_utterance)
        specific_words = [s.lower() for s in processed_str.text.split(" ") if
                          s.lower() not in elicitation_vague_words and s != ""]

        if len(specific_words) == 0:
            # vague query
            return "VagueSearchIntent"

        # specific search
        return "SpecificSearchIntent"

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the PlanningPolicy class.

        This is a complex method that has to deal with a variety of different situations. The
        overall goal of this policy is to search for tasks based on the input the user has provided,
        list the best matching tasks to the user, have the user pick the task they want to perform,
        and then redirect to either the ValidationPolicy or the ExecutionPolicy.

        TODO: some more detail here

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """
        intent_request = IntentRequest()
        intent_request.utterance = session.turn[-1].user_request.interaction.text
        for turn in session.turn:
            intent_request.turns.append(turn)
        # theme_words = session.turn[-1].user_request.interaction.params

        output = OutputInteraction()

        if len(session.turn[-1].user_request.interaction.intents) == 0:

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
                "show_more_details": "QuestionIntent",
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

            logger.info(f"Classified intent: {intent_translation}")
            if intent_translation:
                session.turn[-1].user_request.interaction.intents.append(
                    intent_translation
                )
            else:
                if session.task_selection.theme.theme == "":
                    output.speech_text = random.choice(RIND_FALLBACK_RESPONSE)
                    output = repeat_screen_response(session, output)
                    set_source(output)
                    return session, output

            # fallback in case utterance is classified wrong
            if session.task_selection.theme.theme != "":
                user_utterance = session.turn[-1].user_request.interaction.text
                trigger_theme, _ = should_trigger_theme(user_utterance=user_utterance,
                                                        theme_word=session.task_selection.theme.theme)
                if trigger_theme:
                    if intent_translation != "SearchIntent":
                        logger.info(
                            f'Classified intent {intent_translation}, even though we should have selected theme')

                    theme = self.theme_policy.get_theme(session.task_selection.theme.theme)

                    if theme != "":
                        consume_intents(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=[intent_translation])
                        if intent_translation != "SearchIntent":
                            logger.info(
                                f'Theme {theme} triggered, even though first classification was wrong: '
                                f'{intent_translation}')
                        session.task_selection.theme.theme = theme
                        del session.turn[-1].user_request.interaction.params[:]
                        session.turn[-1].user_request.interaction.params.append(f'search("{theme}")')
                        session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                        session.turn[-1].user_request.interaction.intents.append("SearchIntent")

                    elif intent_translation is None:
                        output.speech_text = random.choice(RIND_FALLBACK_RESPONSE)
                        output = repeat_screen_response(session, output)
                        set_source(output)
                        return session, output

                elif intent_translation is None:
                    output.speech_text = random.choice(RIND_FALLBACK_RESPONSE)
                    output = repeat_screen_response(session, output)
                    set_source(output)
                    return session, output

            elif intent_request.utterance != '' and is_in_user_interaction(
                    user_interaction=session.turn[-1].user_request.interaction,
                    intents_list=["SearchIntent"]):

                theme = self.theme_policy.get_theme(session.turn[-1].user_request.interaction.text)

                if theme != "":
                    logger.info(f"Semantic Searcher matched: {theme}")
                    session.task_selection.theme.theme = theme
                    session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                else:
                    intent = self.__search_intent_builder(
                        query=session.turn[-1].user_request.interaction.text
                    )
                    session.turn[-1].user_request.interaction.intents.append(intent)
        else:
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=["ThemeSearchIntent"]):
                # we are bouncing between policies
                logger.info("Bouncing between policies: theme search decided to send new search")
                session.task_selection.theme.theme = ""
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["ThemeSearchIntent"])
                session.turn[-1].user_request.interaction.intents.append("SpecificSearchIntent")

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ASRErrorIntent']):
            user_utterance = session.turn[-1].user_request.interaction.text
            output.speech_text = random.choice(ASR_ERROR).format(user_utterance)
            output = repeat_screen_response(session, output)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['StopIntent']):
            session.task.phase = Task.TaskPhase.CLOSING
            session.task.state.requirements_displayed = False
            session.task.state.validation_page = 0
            session.task.taskmap.Clear()
            raise PhaseChangeException()

        elif session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:
            if "_button" in session.turn[1].user_request.interaction.text and not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')
            logger.info('in here help corner planning')
            if "_button" in session.turn[-1].user_request.interaction.text:
                del session.turn[-1].user_request.interaction.intents[:]
                session.turn[-1].user_request.interaction.intents.append("InformIntent")
                raise PhaseChangeException()
            session.task.state.help_corner_active = False

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

        # redirect to elicitation if user is confused in elicitation
        if session.task_selection.elicitation_turns == 1 and \
                session.task_selection.categories_elicited == 0 and \
                is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                       intents_list=['ConfusedIntent']) and \
                not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                           intents_list=['Consumed.VagueSearchIntent'],
                                           utterances_list=["what can you do"]):

            _, output = self.elicitation_policy.step(session)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['QuestionIntent']):
            _, output = self.qa_policy.step(
                session
            )
            user_utterance = session.turn[-1].user_request.interaction.text
            output = build_chat_screen(policy_output=output, user_utterance=user_utterance, session=session)
            set_source(output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['ChitChatIntent']):

            if len(session.turn) > 1:
                if not is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                              intents_list=['Consumed.ChitChatIntent']):
                    session, output = self.chitchat_policy.step(session)
                    return session, output
                else:
                    logger.info("Continuing in planner so we don't loop forever")
                    session.turn[-1].user_request.interaction.intents.append('RepeatIntent')
            else:
                session, output = self.chitchat_policy.step(session)
                return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ConfusedIntent",
                                                  "createTimerIntent",
                                                  "pauseTimerIntent",
                                                  "deleteTimerIntent",
                                                  "resumeTimerIntent",
                                                  "showTimerIntent",
                                                  "InformIntent"
                                                  ]):
            raise PhaseChangeException()

        # if taskmap is set we have just displayed the summary page for a pre-selected task
        if session.task.taskmap.taskmap_id != '':
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=["YesIntent", "NextIntent", "ShowRequirementsIntent"],
                                      utterances_list=["show ingredients", "show tools and materials"]) \
                    and len(session.task.taskmap.requirement_list) > 0:
                session.task.phase = Task.TaskPhase.VALIDATING
                session.task.state.safety_warning_said = False
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["ShowRequirementsIntent"])
                raise PhaseChangeException()
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["NoIntent"]):
                session.task.phase = Task.TaskPhase.VALIDATING
                session.task.state.safety_warning_said = False
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["NoIntent"])
                session.task.state.requirements_displayed = True
                raise PhaseChangeException()

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["PreviousIntent", "CancelIntent"]):
                # if we set the utterance to empty, we will not change the query and just
                # re-prompt the previous results to the user
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["CancelIntent", "PreviousIntent"])

                logger.info("CLEAR EVERYTHING")

                intent_request.utterance = ''
                session.error_counter.no_match_counter = 0
                session.task_selection.theme.Clear()
                session.task.taskmap.Clear()

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=['StartTaskIntent', 'YesIntent'],
                                        utterances_list=["start"]):
                session.task.phase = Task.TaskPhase.VALIDATING
                session.task.state.safety_warning_said = False
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["StartTaskIntent", "YesIntent"])
                raise PhaseChangeException()

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=['SearchIntent']):
                session.error_counter.no_match_counter = 0
                session.task_selection.theme.Clear()
                session.task.taskmap.Clear()
                session.task_selection.preferences_elicited = False
                session.task_selection.elicitation_turns = 0
                session.task_selection.results_page = 0
                del session.task_selection.elicitation_utterances[:]
                del session.task_selection.candidates_union[:]

            else:
                speech_requirements = "ingredients" if session.domain == Session.Domain.COOKING else \
                    "things you'll need"
                fallback = {
                    1: [
                        f'Do you want to hear the {speech_requirements}? ',
                    ],
                    2: [
                        f'I can tell you the {speech_requirements} you need for {session.task.taskmap.title}. '
                        'Do you want to hear them? ',
                    ],
                    3: [
                        f"I'm having trouble understanding you. You can say yes if you "
                        f"want to hear the {speech_requirements} for {session.task.taskmap.title}, "
                        f"or say no if you don't.",

                    ]
                }

                if session.error_counter.no_match_counter < 3:
                    session.error_counter.no_match_counter += 1

                if not session.headless:
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    screen = screen_summary_taskmap(session.task.taskmap, speech_req)

                    if len(session.task.taskmap.requirement_list) > 0:
                        screen.hint_text = random.choice(['Show what I need', "what can you do"])
                        screen.buttons.append(f"show {speech_req}")
                        screen.on_click_list.append(f"show {speech_req}")

                    else:
                        session.task.phase = Task.TaskPhase.VALIDATING
                        session.task.state.safety_warning_said = False
                        session.error_counter.no_match_counter = 0
                        consume_intents(session.turn[-1].user_request.interaction,
                                        intents_list=["ShowRequirementsIntent"])
                        raise PhaseChangeException()

                    output.screen.ParseFromString(screen.SerializeToString())

                output.speech_text = random.choice(fallback[session.error_counter.no_match_counter])
                set_source(output)
                return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["CancelIntent", "Consumed.CancelIntent"]):
            route_to_domain(session)

        if not session.task_selection.preferences_elicited and \
                session.task_selection.categories_elicited == 0 and \
                is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                       intents_list=["PreviousIntent"]):
            route_to_domain(session)

        search_again: bool = False
        # Count represent the amount of past utterances to use for search,
        # it does not make any sense to search with 0
        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=[
                                      'SelectIntent',
                                      'MoreResultsIntent',
                                      'PreviousIntent'
                                  ]
                                  ) and session.task_selection.candidates_union and \
                not session.task_selection.preferences_elicited:

            session.task_selection.elicitation_turns = 0
            index = intent_classification.attributes.option
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=[
                                          'MoreResultsIntent',
                                          'PreviousIntent']
                                      ) and session.task_selection.category.title != "":

                logger.info("Category flow triggered")
                updated_session, cat_output = self.category_policy.step(session)

                if session.task_selection.elicitation_turns == 0:
                    intent_request.utterance = session.turn[-1].user_request.interaction.text
                    search_again = True

                elif updated_session is not None and cat_output is not None:
                    set_source(cat_output)
                    return updated_session, cat_output

            if 0 < index <= 3:
                # RinD only gets three tasks to select from at a time
                if session.task_selection.categories_elicited >= 2:
                    task_idx = index - 1  # we only have 3 tasks in each subcategory
                elif session.task_selection.results_page > 10 and not session.headless:
                    session.task_selection.results_page -= 3
                    task_idx = index - 1 + session.task_selection.results_page
                else:
                    task_idx = index - 1 + session.task_selection.results_page

                if session.task_selection.candidates_union[task_idx].HasField(
                        'task') and session.task_selection.categories_elicited != 1:
                    session.task.taskmap.ParseFromString(
                        session.task_selection.candidates_union[task_idx].task.SerializeToString())
                elif session.task_selection.categories_elicited >= 1:
                    # redirect to subcategory display or taskmap display for a subcategory
                    updated_session, cat_output = self.category_policy.step(session)
                    if updated_session is not None and cat_output is not None:
                        set_source(cat_output)
                        return updated_session, cat_output
                else:  # select a category
                    session.task_selection.category.Clear()
                    session.task_selection.category.MergeFrom(
                        session.task_selection.candidates_union[task_idx].category)
                    logger.info(f"New Category Title - {session.task_selection.category.title}")
                    consume_intents(session.turn[-1].user_request.interaction, intents_list=["SelectIntent"])
                    session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
                    updated_session, cat_output = self.category_policy.step(session)

                    if updated_session is not None and cat_output is not None:
                        logger.info("elicitation turn NOT NONE and outputs are NONE")
                        set_source(cat_output)
                        return updated_session, cat_output

                if session.headless:
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    output.speech_text = f"{headless_task_summary(session.task.taskmap, speech_req)}. "
                    output.speech_text += random.choice(INGREDIENT_FUNNY_REMARK).format("them", "hear")
                    set_source(output)
                    return session, output
                else:
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    screen = screen_summary_taskmap(session.task.taskmap, speech_req)

                    COMPLEMENT_USER_ON_SELECTION = [
                        "Awesome pick! ",
                        "Great choice! ",
                        "Great! ",
                        "Got it! ",
                    ]

                    complement = random.choice(COMPLEMENT_USER_ON_SELECTION)
                    output.speech_text = f"{complement} In that case, let's have a quick overview of the task. "

                    if len(session.task.taskmap.requirement_list) > 0:

                        output.speech_text += random.choice(INGREDIENT_FUNNY_REMARK).format(speech_req, "see")
                        screen.hint_text = 'Show what I need'
                        screen.buttons.append(f"show {speech_req}")
                        screen.on_click_list.append(f"show {speech_req}")

                    else:
                        session.task.phase = Task.TaskPhase.VALIDATING
                        session.error_counter.no_match_counter = 0
                        consume_intents(session.turn[-1].user_request.interaction,
                                        intents_list=["ShowRequirementsIntent"])
                        raise PhaseChangeException()

                    output.screen.ParseFromString(screen.SerializeToString())
                    set_source(output)
                    return session, output
            else:
                if not search_again and not is_in_user_interaction(
                        user_interaction=session.turn[-1].user_request.interaction,
                        intents_list=['MoreResultsIntent']):
                    output.speech_text = random.choice(OUT_OF_RANGE_COREF_RESPONSE)
                    output = repeat_screen_response(session, output)
                    set_source(output)
                    return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["YesIntent"]):
            output = repeat_screen_response(session, output)
            output.speech_text = f"{random.choice(YES_PLANNING)}"

            candidates_speech_text = populate_choices(session.task_selection.candidates_union)
            output.speech_text += candidates_speech_text
            output.speech_text += "Which would you like? "
            set_source(output)
            return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["NoIntent"]):
            route_to_domain(session)

        # select category from elicitation policy
        if session.task_selection.preferences_elicited is True and is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["SelectIntent"]):

            session.task_selection.elicitation_turns = 0

            index = intent_classification.attributes.option
            task_idx = index - 1 + session.task_selection.results_page

            session.task_selection.category.Clear()
            if len(session.task_selection.candidates_union) > task_idx:
                session.task_selection.category.MergeFrom(session.task_selection.candidates_union[task_idx].category)
            logger.info("NEW CATEGORY TITLE")
            logger.info(session.task_selection.category.title)
            consume_intents(session.turn[-1].user_request.interaction, intents_list=["SelectIntent"])
            session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")
            updated_session, cat_output = self.category_policy.step(session)

            if updated_session is not None and cat_output is not None:
                logger.info("elicitation turn NOT NONE and outputs are NONE")
                set_source(cat_output)
                return updated_session, cat_output

        # Search Again only if we are changing the query utterances that we are using
        if not search_again and (intent_request.utterance != '' and is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["SearchIntent"]) or session.task_selection.theme.theme != ""
                                 or not session.task_selection.preferences_elicited):

            if session.task_selection.theme.theme != "":

                updated_session, theme_output = self.theme_policy.step(session)

                if updated_session is not None and theme_output is not None:
                    set_source(theme_output)
                    return updated_session, theme_output

            elif not session.task_selection.candidates_union and \
                    not session.task_selection.preferences_elicited and \
                    is_in_user_interaction(
                        user_interaction=session.turn[-1].user_request.interaction,
                        intents_list=["PreviousIntent", "Consumed.PreviousIntent"]):

                logger.info("ROUTING TO DOMAIN")

                route_to_domain(session)

            elif session.task_selection.category.title != "":
                logger.info(f"Intents we have: {session.turn[-1].user_request.interaction.intents}")
                updated_session, cat_output = self.category_policy.step(session)

                if updated_session is not None and cat_output is not None:
                    set_source(cat_output)
                    return updated_session, cat_output

            # for specific search
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["SpecificSearchIntent"]):
                session.task_selection.results_page = 0
                session.task_selection.elicitation_utterances.append(intent_request.utterance)
                search_again = True

            # for specific search
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["VagueSearchIntent"]):
                _, output = self.elicitation_policy.step(session)
                set_source(output)
                return session, output

        dangerous_assessment = self.dangerous_task_filter.dangerous_query_check(session)
        if dangerous_assessment.is_dangerous:
            output.speech_text = random.choice(DANGEROUS_TASK_RESPONSES)
            session, output = close_session(session, output)
            set_source(output)
            return session, output

        if search_again:
            # Get search results
            query: SearchQuery = self.query_builder.synthesize_query(session)
            search_results = self.searcher.search_taskmap(query)
            candidate_list = search_results.candidate_list

            # Remove previous results and save results in session
            del session.task_selection.candidates_union[:]
            for candidate in candidate_list.candidates:
                union = TaskmapCategoryUnion()
                if candidate.HasField('task'):
                    candidate = candidate.task
                    if candidate.rating_out_100 is None or candidate.rating_out_100 < 80 \
                            or candidate.rating_count is not None:
                        candidate.rating_out_100 = random.randint(80, 100)
                        candidate.rating_count = random.randint(5, 15)
                    union.task.CopyFrom(candidate)
                elif candidate.HasField('category'):
                    candidate = candidate.category
                    union.category.CopyFrom(candidate)
                new_c = session.task_selection.candidates_union.add()
                new_c.ParseFromString(union.SerializeToString())

        else:
            candidate_list: CandidateList = CandidateList()
            for candidate in session.task_selection.candidates_union:
                if candidate.HasField('task'):
                    task = candidate.task
                    if task.rating_out_100 is None or task.rating_out_100 < 80 \
                            or task.rating_count is None:
                        task.rating_out_100 = random.randint(80, 100)
                        task.rating_count = random.randint(5, 15)
                    new_c = candidate_list.candidates.add()
                    union = TaskmapCategoryUnion()
                    union.task.CopyFrom(task)
                    new_c.ParseFromString(union.SerializeToString())
                else:
                    category = candidate.category
                    new_c = candidate_list.candidates.add()
                    union = TaskmapCategoryUnion()
                    union.category.CopyFrom(category)
                    new_c.ParseFromString(union.SerializeToString())

        ''' 
        === Populate search results in Response ===
        '''
        # an empty user utterance in search usually happens when the user says cancel in the detail page
        # thus we don't say the search terms.
        if intent_request.utterance == "" or is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["Consumed.NoIntent", "Consumed.PreviousIntent"]):
            output.speech_text = f"Okay, these were the top matches I found earlier. "

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ThemeSearchIntent"]):
            if session.task_selection.theme.theme != "":
                search_term = session.task_selection.theme.theme
            else:
                search_term = session.turn[-1].user_request.interaction.text

            theme_responses: list = [
                f"I have three great recommendations for '{search_term}'. ",
                f"Well, for  '{search_term}', you can try one of my three all-time favorites.  "
            ]
            output.speech_text = random.choice(theme_responses)

        elif session.task_selection.preferences_elicited:
            # ideally we give the user a reason for recommendation, but can only do it with Spacy :(
            elicitation_responses = [
                "Okay, I think you might enjoy one of these. Say cancel if you\'d like to start over. "
            ]
            output.speech_text = random.choice(elicitation_responses)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["RepeatIntent"]):
            repeat_responses = ['Let me quickly recap that for you. ', 'Let me go over that again. ']
            output.speech_text = random.choice(repeat_responses)
        else:
            if session.headless:
                output.speech_text = f"I understood: {session.turn[-1].user_request.interaction.text}. " \
                                     f"The best matches I could find for you are the following: "
            else:
                if session.domain == Session.Domain.COOKING:
                    regular_responses_cooking = [
                        "You got it! I've found three fantastic matches for you. ",
                        'Mmm, it looks like you have an excellent taste in food! '
                        'These are the best recipes I know of! ',
                        'Got it, I quickly analyzed all my favorite recipes and I believe these will be the best for '
                        'you. ',
                        'Certainly! How about these three matches? They look so tasty! ',
                        "Yum! I can already tell that you have a great taste in food! Here are some suggestions I "
                        "came up with on the spot. ",
                    ]
                    output.speech_text = random.choice(regular_responses_cooking)

                else:
                    regular_responses = [
                        'I quickly found these three great matches for you. ',
                        'Sure, these are my favourites! ',
                        'Got it, these are my favourites! ',
                        'How about these three matches? ',
                        'Got it, these tutorials look interesting!  ',
                        'Sounds good! Here are my top three picks. ',
                    ]
                    output.speech_text = random.choice(regular_responses)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["MoreResultsIntent", "NextIntent"]) and \
                len(session.task_selection.candidates_union) > 0:

            if session.task_selection.results_page < len(session.task_selection.candidates_union):
                session.task_selection.results_page += 3

            if session.task_selection.results_page >= len(session.task_selection.candidates_union):
                output.speech_text = random.choice(ALL_RESULTS_PROMPT)
                output = repeat_screen_response(session, output)
                logger.info("repeat results on the screen")
            else:
                output.speech_text = random.choice(MORE_RESULTS_INTRO)
                logger.info("populate more results")

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["PreviousIntent"]):

            if session.task_selection.results_page > 0:

                if not session.headless and session.task_selection.results_page > len(
                        session.task_selection.candidates_union):
                    # we repeated screen so go back two pages
                    session.task_selection.results_page -= 6
                elif session.task_selection.results_page > 0:
                    session.task_selection.results_page -= 3

                if session.task_selection.results_page == 0:
                    output.speech_text = random.choice(FIRST_RESULT_SET_PROMPT)
                else:
                    output.speech_text = random.choice(PREVIOUS_RESULTS_INTRO)
            else:
                route_to_domain(session)

        # if we don't have results by now, we did something wrong - this means we need to reroute
        if len(session.task_selection.candidates_union) == 0:
            route_to_domain(session)

        if session.task_selection.results_page < len(session.task_selection.candidates_union):
            results_page = session.task_selection.results_page
            candidates_speech_text = populate_choices(candidate_list.candidates[results_page:results_page + 3])
            output.speech_text += candidates_speech_text

        if not session.headless:
            if (
                    intent_request.utterance == ""
                    or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                              intents_list=["Consumed.NoIntent"])
                    or intent_request.utterance is None
                    or (session.domain == Session.Domain.COOKING and session.task_selection.preferences_elicited)
                    or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                              intents_list=["MoreResultsIntent", "NextIntent", "PreviousIntent"])
            ):
                output.screen.headline = f'I understood: "{intent_request.utterance}"'
            else:
                output.screen.headline = f'I understood: "{intent_request.utterance}"'

            results_page = session.task_selection.results_page
            on_click_list = display_screen_results(
                candidate_list.candidates[results_page:results_page + 3], output, session.domain
            )

            output.screen.on_click_list.extend(on_click_list)

        if intent_request.utterance != "":
            if not session.headless:
                options = SELECT_POSSIBILITY.copy()
                options.append('You can select one of the results by saying its name, '
                               'or clicking the image on the screen. ')
                output.speech_text += random.choice(options)
            else:
                output.speech_text += random.choice(SELECT_POSSIBILITY)

        TUTORIAL1 = 'You can start a new search by saying "cancel" or "restart".'

        TUTORIAL2_UI = 'You can select one of the results by saying its name, ' \
                       ' or clicking the image on the screen.'
        TUTORIAL2_HL = 'You can select one of the results by saying ' \
                       'the name of the result'

        if session.headless:
            tutorial_list = [TUTORIAL1, TUTORIAL2_HL]
        else:
            REPROMPTS = ["the first one", "more results", "which one can you recommend?", "which should I choose?"]
            if len(candidate_list.candidates) > 0:
                results_page = session.task_selection.results_page
                if results_page < 9 and results_page + 3 < len(candidate_list.candidates):
                    first = candidate_list.candidates[results_page]
                    if not any(x == first for x in candidate_list.candidates[results_page:results_page + 3]):
                        REPROMPTS.append(
                            f"{random.choice(candidate_list.candidates[results_page:results_page + 3]).title} please")
            output.screen.hint_text = random.sample(REPROMPTS, 1)[0]
            tutorial_list = [TUTORIAL1, TUTORIAL2_UI]

        chosen_tutorial = random.sample(tutorial_list, 1)[0]
        output.reprompt = chosen_tutorial
        set_source(output)
        return session, output
