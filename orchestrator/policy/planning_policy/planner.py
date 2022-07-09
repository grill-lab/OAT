import grpc
import os
import random

from policy.abstract_policy import AbstractPolicy
from .theme_policy import ThemePolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from .elicitation_policy import ElicitationPolicy
from taskmap_pb2 import Session, OutputInteraction, Task, Image, ScreenInteraction, TaskMap, InputInteraction
from searcher_pb2 import SearchQuery, TaskMapList
from exceptions import PhaseChangeException

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import IntentRequest

from utils import logger, close_session, is_in_user_interaction, \
    consume_intents, screen_summary_taskmap, repeat_screen_response, get_star_string, format_author, \
        indri_stop_words, theme_recommendations, format_author_headless, headless_task_summary, \
        DANGEROUS_TASK_RESPONSES, MORE_RESULTS_FALLBACK, MORE_RESULTS_INTRO, PREVIOUS_RESULTS_INTRO, \
        ALL_RESULTS_PROMPT, FIRST_RESULT_SET_PROMPT, RIND_FALLBACK_RESPONSE, OUT_OF_RANGE_COREF_RESPONSE,\
        YES_PLANNING, NO_PLANNING, RIND_FALLBACK_RESPONSE, \
        SELECT_POSSIBILITY, ASR_ERROR, CHIT_CHAT, display_screen_results, populate_choices

from searcher_pb2_grpc import SearcherStub, QueryBuilderStub
from dangerous_task_pb2_grpc import DangerousStub
from database_pb2_grpc import DatabaseStub
from theme_pb2 import ThemeRequest



def route_to_domain(session):
    consume_intents(session.turn[-1].user_request.interaction,
                            intents_list=["CancelIntent", "AMAZON.CancelIntent"])

    session.task_selection.preferences_elicited = False
    session.task_selection.elicitation_turns = 0
    session.task_selection.results_page = 0
    session.domain = Session.Domain.UNKNOWN
    del session.task_selection.elicitation_utterances[:]
    session.task_selection.theme.Clear()

    session.task.phase = Task.TaskPhase.DOMAIN
    raise PhaseChangeException()


class PlannerPolicyV2(AbstractPolicy):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(
            os.environ["NEURAL_FUNCTIONALITIES_URL"])
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])

        self.searcher = SearcherStub(channel)
        self.query_builder = QueryBuilderStub(channel)
        self.dangerous_task_filter = DangerousStub(channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(
            neural_channel)

        self.database = DatabaseStub(external_channel)

        self.theme_policy = ThemePolicy()
        self.qa_policy = DefaultQAPolicy()
        self.elicitation_policy = ElicitationPolicy()
    
    def __search_intent_builder(self, query):
        """ Assert whether query a theme query (i.e. words map to specified theme). """
        # Find specific words by removing stopwords.
        vague_words = [
            'build', 'bake', 'quick', '', 
            'home', 'improvement', 'homeimprovement', 
            'fix', 'eat', 'search'
        ]
        stopwords = indri_stop_words + vague_words
        specific_words = [s.lower() for s in query.split(" ") if s.lower() not in stopwords]

        if len(specific_words) == 0:
            # vague query
            return "VagueSearchIntent"

        # specific search
        return "SpecificSearchIntent"

    def step(self, session: Session) -> (Session, OutputInteraction):

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
                "show_more_details": "ConfusedIntent",
                "next": "NextIntent",
                "previous": "PreviousIntent",
                "stop": "StopIntent",
                "chit_chat": "ChitChatIntent",
                "ASR_error": "ASRErrorIntent",
                "answer_question": "QuestionIntent",
                "inform_capabilities": "ConfusedIntent",
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
                return session, output

            if intent_request.utterance is not '' and is_in_user_interaction(
                    user_interaction=session.turn[-1].user_request.interaction,
                    intents_list=["SearchIntent"]):

                theme = self.theme_policy.get_theme(session.turn[-1].user_request.interaction)

                if theme != "":
                    logger.info(f"Semantic Searcher matched: {theme}")
                    session.task_selection.theme.theme = theme
                    session.turn[-1].user_request.interaction.intents.append("ThemeSearchIntent")

                else:
                    intent = self.__search_intent_builder(
                        query=session.turn[-1].user_request.interaction.text
                    )
                    session.turn[-1].user_request.interaction.intents.append(intent)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ASRErrorIntent']):
            user_utterance = session.turn[-1].user_request.interaction.text
            output.speech_text = random.choice(ASR_ERROR).format(user_utterance)
            output = repeat_screen_response(session, output)
            return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ChitChatIntent', 'QuestionIntent']):
            _, output = self.qa_policy.step(
                session
            )
            output = repeat_screen_response(session, output)
            return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['StopIntent', 'AMAZON.StopIntent']):
            session.task.phase = Task.TaskPhase.CLOSING
            session.task.state.requirements_displayed = False
            session.task.state.validation_page = 0
            session.task.taskmap.Clear()
            raise PhaseChangeException()

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ConfusedIntent",
                                                  "createTimerIntent",
                                                  "pauseTimerIntent",
                                                  "deleteTimerIntent",
                                                  "resumeTimerIntent",
                                                  "showTimerIntent"
                                                  ]):
            raise PhaseChangeException()

        # if taskmap is set we have just displayed the summary page for a pre-selected task
        if session.task.taskmap.taskmap_id != '':
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=["YesIntent", "NextIntent", "ShowRequirementsIntent"],
                                      utterances_list=["show ingredients", "show tools and materials"])\
                    and len(session.task.taskmap.requirement_list) > 0:
                session.task.phase = Task.TaskPhase.VALIDATING
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["ShowRequirementsIntent"])
                raise PhaseChangeException()
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["NoIntent"]):
                session.task.phase = Task.TaskPhase.VALIDATING
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["NoIntent"])
                session.task.state.requirements_displayed = True
                raise PhaseChangeException()

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["PreviousIntent", "CancelIntent", "AMAZON.CancelIntent"]):
                # if we set the utterance to empty, we will not change the query and just
                # reprompt the previous results to the user
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["CancelIntent", "AMAZON.CancelIntent", "PreviousIntent"])

                intent_request.utterance = ''
                session.error_counter.no_match_counter = 0
                session.task_selection.theme.Clear()
                session.task.taskmap.Clear()

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=['StartTaskIntent', 'YesIntent'],
                                        utterances_list=["start"]):
                session.task.phase = Task.TaskPhase.EXECUTING
                session.error_counter.no_match_counter = 0
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["StartTaskIntent", "YesIntent"])
                raise PhaseChangeException()

            else:
                speech_requirements = "ingredients" if session.domain == Session.Domain.COOKING else "things you'll need"
                fallback = {
                    1 : [
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
                
                output = repeat_screen_response(session, output)
                output.speech_text = random.choice(fallback[session.error_counter.no_match_counter])
                return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["CancelIntent", "AMAZON.CancelIntent"]):

            route_to_domain(session)

        # Count represent the amount of past utterances to use for search,
        # it does not make any sense to search with 0
        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['SelectIntent']) and session.task_selection.candidates:

            index = intent_classification.attributes.option
            
            if 0 < index <= 3: #len(session.task_selection.candidates):
                # RinD only gets three tasks to select from at a time
                if session.task_selection.results_page > 10 and not session.headless:
                    session.task_selection.results_page -= 3
                    task_idx = index - 1 + session.task_selection.results_page
                else:
                    task_idx = index - 1 + session.task_selection.results_page
                session.task.taskmap.ParseFromString(session.task_selection.candidates[task_idx].SerializeToString())

                if session.headless:
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    output.speech_text = f"{headless_task_summary(session.task.taskmap, speech_req)}. "
                    output.speech_text += f" Do you want to hear them?"
                    return session, output
                else:
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    screen = screen_summary_taskmap(session.task.taskmap, speech_req)

                    output.speech_text = f"Here is the summary of the task. "

                    if len(session.task.taskmap.requirement_list) > 0:
                        output.speech_text += f'Do you want to see the {speech_req}? '
                        screen.hint_text = 'Show what I need'
                        screen.buttons.append(f"show {speech_req}")
                        screen.on_click_list.append(f"show {speech_req}")

                    else:
                        task_type = "recipe" if session.domain == Session.Domain.COOKING else "task"

                        output.speech_text += f'There are no {speech_req} for this {task_type}. ' \
                                              f'Are you ready to start?'
                        screen.hint_text = 'Start'
                        screen.buttons.append(f"Start")
                        screen.on_click_list.append(f"Start")

                    output.screen.ParseFromString(screen.SerializeToString())
                    return session, output
            else:
                output.speech_text = random.choice(OUT_OF_RANGE_COREF_RESPONSE)
                output = repeat_screen_response(session, output)
                return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["YesIntent"]):
            output = repeat_screen_response(session, output)
            output.speech_text = f"{random.choice(YES_PLANNING)}"

            candidates_speech_text = populate_choices(session.task_selection.candidates)
            output.speech_text += candidates_speech_text
            output.speech_text += "Which would you like? "
            return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["NoIntent"]):
            route_to_domain(session)

        # Search Again only if we are changing the query utterances that we are using
        search_again: bool = False
        if intent_request.utterance is not '' and is_in_user_interaction(
                user_interaction=session.turn[-1].user_request.interaction,
                intents_list=["SearchIntent"]) or session.task_selection.theme.theme != "" \
                    or not session.task_selection.preferences_elicited:

            # theme search
            if session.task_selection.theme.theme != "":
                
                logger.info("CALLING THEME POLICY!!!!!!!!!!!!")
                logger.info(session.task_selection.theme)
                logger.info(f"Intents we have: {session.turn[-1].user_request.interaction.intents}")
                updated_session, theme_output = self.theme_policy.step(session)

                if updated_session is not None and theme_output is not None:
                    return updated_session, theme_output

            # for specific search
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["SpecificSearchIntent"]):
                session.task_selection.results_page = 0
                session.task_selection.elicitation_utterances.append(intent_request.utterance)
                # if len(session.task_selection.elicitation_utterances) > 1:
                #     # we went into theme search
                #     session.task_selection.elicitation_utterances.reverse()
                logger.info(session.task_selection.elicitation_utterances)
                search_again = True
            
            # for specific search
            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["VagueSearchIntent"]):
                logger.info("CALLING ELICITATION POLICY")
                _, output = self.elicitation_policy.step(session)
                return session, output

        dangerous_assessment = self.dangerous_task_filter.dangerous_query_check(session)
        if dangerous_assessment.is_dangerous:
            logger.info("USER WANTS TO PERFORM A DANGEROUS TASK!")
            output.speech_text = random.choice(DANGEROUS_TASK_RESPONSES)
            session, output = close_session(session, output)
            return session, output

        if search_again:
            # Get search results
            query: SearchQuery = self.query_builder.synthesize_query(session)
            search_results = self.searcher.search_taskmap(query)
            taskmap_list = search_results.taskmap_list

            # Remove previous results and save results in session
            del session.task_selection.candidates[:]
            for candidate in taskmap_list.candidates:
                if candidate.rating_out_100 is None or candidate.rating_out_100 < 80 \
                        or candidate.rating_count is not None:
                    candidate.rating_out_100 = random.randint(80, 100)
                    candidate.rating_count = random.randint(5, 15)
                new_c = session.task_selection.candidates.add()
                new_c.ParseFromString(candidate.SerializeToString())
        else:
            taskmap_list: TaskMapList = TaskMapList()
            for candidate in session.task_selection.candidates:
                if candidate.rating_out_100 is None or candidate.rating_out_100 < 80 \
                        or candidate.rating_count is None:
                    candidate.rating_out_100 = random.randint(80, 100)
                    candidate.rating_count = random.randint(5, 15)
                taskmap = taskmap_list.candidates.add()
                taskmap.ParseFromString(candidate.SerializeToString())

        ''' 
        === Populate search results in Response ===
        '''
        # an empty user utterance in search usually happens when the user says cancel in the detail page
        # thus we don't say the search terms.
        if intent_request.utterance == "" or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["Consumed.NoIntent", "Consumed.PreviousIntent"]):
            output.speech_text = f"Okay, these were the top matches I found earlier. "
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ThemeSearchIntent"]):
            theme_responses: list = [
                f"I have three great recommendations for '{session.task_selection.theme.theme}'. ",
                f"Well, for  '{session.task_selection.theme.theme}', you can try one of my three all-time favorites.  "
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
            repeat_responses = ['To repeat. ', 'Again ']
            output.speech_text = random.choice(repeat_responses)
        else:
            no_stop_words = " ".join([w for w in intent_request.utterance.split(" ") if w not in indri_stop_words])
            regular_responses = [
                f'So, for "{no_stop_words}", I found three great matches. ',
            ]
            output.speech_text = random.choice(regular_responses)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["MoreResultsIntent", "NextIntent"]):

            if session.task_selection.results_page < len(session.task_selection.candidates):
                session.task_selection.results_page += 3

            if session.task_selection.results_page >= len(session.task_selection.candidates):
                output.speech_text = random.choice(ALL_RESULTS_PROMPT)
                output = repeat_screen_response(session, output)
            else:
                output.speech_text = random.choice(MORE_RESULTS_INTRO)
        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["PreviousIntent"]):
            if session.task_selection.results_page > 0:

                if not session.headless and session.task_selection.results_page > len(session.task_selection.candidates):
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

        if session.task_selection.results_page < len(session.task_selection.candidates):
            results_page = session.task_selection.results_page
            candidates_speech_text = populate_choices(taskmap_list.candidates[results_page:results_page+3])
            output.speech_text += candidates_speech_text

        if not session.headless:
            results_page = session.task_selection.results_page
            if (
                intent_request.utterance == ""
                or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=["Consumed.NoIntent"])
                or intent_request.utterance is None
                or (session.domain == Session.Domain.COOKING and session.task_selection.preferences_elicited)
                or is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=["MoreResultsIntent", "NextIntent", "PreviousIntent"])
            ):
                output.screen.headline = f'Say "cancel" to go back.'
            else:
                output.screen.headline = f'"{intent_request.utterance}". Say "cancel" to go back.'

            results_page = session.task_selection.results_page
            on_click_list = display_screen_results(
                taskmap_list.candidates[results_page:results_page+3], output
            )

            output.screen.on_click_list.extend(on_click_list)
            output.screen.background = 'https://grill-bot-data.s3.amazonaws.com/images/multi_domain_default.jpg'
            # output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

            # idx: int
            # candidate: TaskMap
            # on_click_list = []
            # results_page = session.task_selection.results_page
            # for idx, candidate in enumerate(taskmap_list.candidates[results_page:results_page+3]):
            #     image: Image = output.screen.image_list.add()

            #     image.path = candidate.thumbnail_url
            #     image.title = candidate.title

            #     if candidate.author is not None and candidate.author != "":
            #          image.description = f"By {format_author(candidate.author)}"
            #     elif candidate.domain_name is not None and candidate.domain_name != "":
            #         image.description = f"By {candidate.domain_name}"
            #     else:
            #         image.title = candidate.title

            #     if candidate.rating_out_100 is not None and candidate.rating_out_100 != 0 \
            #             and candidate.rating_count is not None:
            #         rating = candidate.rating_out_100 / 20
            #     else:
            #         rating = random.uniform(4, 5)
            #     image.ratingValue = rating

            #     on_click_list.append(str(idx+1))

            # output.screen.on_click_list.extend(on_click_list)

        if intent_request.utterance != "":
            if not session.headless:
                options = SELECT_POSSIBILITY.copy()
                options.append('You can select one of the results by saying its name, '
                               'or clicking the image on the screen. ')
                output.speech_text += random.choice(options)
            else:
                output.speech_text += random.choice(SELECT_POSSIBILITY)

        if session.task_selection.results_page < len(session.task_selection.candidates):
            output.speech_text += "Which would you like?"

        TUTORIAL1 = 'You can start a new search by saying "cancel" or "restart".'

        TUTORIAL2_UI = 'You can select one of the results by saying its name, ' \
                       ' or clicking the image on the screen.'
        TUTORIAL2_HL = 'You can select one of the results by saying ' \
                       'the name of the result'

        if session.headless:
            tutorial_list = [TUTORIAL1, TUTORIAL2_HL]
        else:
            REPROMPTS = ["the first one", "more results", "which one can you recommend?", "which should I choose?"]
            if len(taskmap_list.candidates) > 0:
                results_page = session.task_selection.results_page
                first = taskmap_list.candidates[results_page]
                if not any(x == first for x in taskmap_list.candidates[results_page:results_page + 3]):
                    REPROMPTS.append(
                        f"{random.choice(taskmap_list.candidates[results_page:results_page + 3]).title} please")
            output.screen.hint_text = random.sample(REPROMPTS, 1)[0]
            tutorial_list = [TUTORIAL1, TUTORIAL2_UI]

        chosen_tutorial = random.sample(tutorial_list, 1)[0]
        output.reprompt = chosen_tutorial

        return session, output
