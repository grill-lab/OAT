import os
import random
import grpc

from typing import List, Tuple

from exceptions import PhaseChangeException
from phase_intent_classifier_pb2 import IntentRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub

from policy.abstract_policy import AbstractPolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from policy.chitchat_policy import DefaultPolicy as DefaultChitChatPolicy

from task_manager_pb2 import InfoRequest, InfoResponse
from task_manager_pb2_grpc import TaskManagerStub
from llm_pb2_grpc import LLMReplacementGenerationStub

from taskmap_pb2 import OutputInteraction, Session, Task
from utils import (
    ASR_ERROR,
    RIND_FALLBACK_RESPONSE,
    consume_intents,
    is_in_user_interaction,
    logger,
    repeat_screen_response,
    screen_summary_taskmap,
    set_source,
    show_ingredients_screen,
    build_chat_screen,
    REPLACE_SUGGESTION,
    PROMOTE_SUBSTIUTIONS
)


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
                    intents_list=["CancelIntent", "NoIntent", "PreviousIntent"])
    session.task.phase = Task.TaskPhase.PLANNING
    session.task.state.requirements_displayed = False
    session.task.state.validation_courtesy = False
    session.task.state.help_corner_active = False
    session.task.state.joke_uttered = False
    session.task.state.tip_uttered = False
    session.task.state.validation_page = 0
    session.task_selection.results_page = 0
    session.task_selection.categories_elicited = 0
    session.task.taskmap.Clear()
    session.task.state.safety_warning_said = False
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
    session.task.state.help_corner_active = False
    session.task.state.validation_page = 0
    session.error_counter.no_match_counter = 0
    raise PhaseChangeException()


def route_to_domain(session):
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["SearchIntent"])

    session.task_selection.preferences_elicited = False
    session.task.state.joke_uttered = False
    session.task.state.tip_uttered = False
    session.task_selection.elicitation_turns = 0
    session.task_selection.results_page = 0
    session.domain = Session.Domain.UNKNOWN
    del session.task_selection.elicitation_utterances[:]
    del session.task_selection.candidates_union[:]
    session.task_selection.category.Clear()
    session.task_selection.theme.Clear()
    session.task.taskmap.Clear()
    session.task.state.Clear()
    session.task.phase = Task.TaskPhase.DOMAIN
    del session.turn[-1].user_request.interaction.intents[:]
    raise PhaseChangeException()


class ValidationPolicy(AbstractPolicy):
    SAFETY_WARNING = 'Before we get started, please be careful when using any tools or equipment. ' \
                     'Remember, safety first! '

    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])

        self.task_manager: TaskManagerStub = TaskManagerStub(channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(
            neural_channel)
        self.qa_policy = DefaultQAPolicy()
        self.chitchat_policy = DefaultChitChatPolicy()
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.replacement_step_rewriter = LLMReplacementGenerationStub(channel)

    def build_ingredients_output(self, session, output):

        requirements_list = self.__get_requirements_utterances(session)
        WANT_TO_START = f' Should we get started? '

        if len(requirements_list) == 0:
            session.task.state.requirements_displayed = True

            output.speech_text = ""
            if not session.headless:
                speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                screen = screen_summary_taskmap(session.task.taskmap, speech_req)
                # add start with task button
                domain = "Recipe" if session.domain == Session.Domain.COOKING else "Task"
                screen.buttons.append(f"Start")
                screen.on_click_list.append(f"start {domain}")
                screen.hint_text = 'Start'
                output.screen.ParseFromString(screen.SerializeToString())
            task_type = "recipe" if session.domain == Session.Domain.COOKING else "task"
            output.speech_text += f'This {task_type} has no requirements! But, ' + \
                                  self.SAFETY_WARNING + WANT_TO_START

        else:
            if not session.headless:
                domain = "recipe" if session.domain == Session.Domain.COOKING else "task"
                if session.task.taskmap.domain_name == "ai_generated":
                    if not session.task.state.safety_warning_said:
                        output.speech_text = self.SAFETY_WARNING + f'Especially since I just generated this {domain}' \
                                                                   f' for you. '
                        session.task.state.safety_warning_said = True
                    else:
                        output.speech_text = f"I just finished generating this {domain} for you. "
                else:
                    output.speech_text = ""

                ingredients_output: OutputInteraction = show_ingredients_screen(session, requirements_list, output)

                said_promotions = False

                if session.task.taskmap.domain_name != "wikihow" and session.task.taskmap.domain_name != "ai_generated":
                    output.speech_text += random.choice(PROMOTE_SUBSTIUTIONS)
                    said_promotions = True
                elif not session.task.state.safety_warning_said:
                    output.speech_text += self.SAFETY_WARNING
                    session.task.state.safety_warning_said = True

                # add start with task button
                speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                ingredients_output.screen.buttons.append(f"Read")
                ingredients_output.screen.on_click_list.append(f"show the {speech_req}")
                short_reqs = [req for req in self.__get_requirements_utterances(session, amount=False) if len(req) < 15]
                if len(short_reqs) > 0:
                    example_req = random.choice(short_reqs)
                    options = [
                        f"Can I replace {example_req}?",
                        f"Can I replace {example_req} with ... ?",
                        # f"I don't like {example_req}",
                    ]
                    chosen_option = random.choice(options)
                else:
                    chosen_option = "Start"
                ingredients_output.screen.buttons.append("Start")
                ingredients_output.screen.on_click_list.append("Start")
                ingredients_output.screen.hint_text = chosen_option
                output.screen.ParseFromString(ingredients_output.screen.SerializeToString())

                if said_promotions:
                    output.speech_text += random.choice(
                        [f"Or say start to start the {domain}. ", f"Or say start to begin the {domain}. "])
                else:
                    if not session.task.state.safety_warning_said:
                        output.speech_text += self.SAFETY_WARNING
                        session.task.state.safety_warning_said = True
                    output.speech_text += WANT_TO_START
                session.task.state.requirements_displayed = True
            else:
                output.speech_text = ''
                if session.task.state.validation_page != 0:

                    if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                              intents_list=["PreviousIntent"]):
                        session.task.state.validation_page -= 6
                    elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                                intents_list=["RepeatIntent"]):
                        session.task.state.validation_page -= 3

                subset = requirements_list[session.task.state.validation_page:][:3]
                subset = [f"{idx + 1}. {item}" if str(idx + 1) not in item else f"{item}" for idx, item in
                          enumerate(subset)]
                output.speech_text += self.verbal_progress(session, len(requirements_list))
                if len(subset) > 1:
                    output.speech_text += '. '.join(subset[:-1]) + '. ' + ' And, ' + subset[-1] + '. '
                else:
                    output.speech_text += '. '.join(subset) + '. '

                num_req = len(requirements_list)
                if session.task.state.validation_page == 0 and \
                        num_req > 3 and not \
                        session.task.state.validation_courtesy:

                    if session.domain == Session.Domain.COOKING:
                        req_type = "ingredients"
                    else:
                        req_type = "things you'll need"
                    output.speech_text += f'Just so you know, I\'ll tell you the {req_type} three at a time. ' \
                                          f'You can ask me to say the next three, or repeat the ones I just told you. '

                    # we don't have to tell the user again this tid bit again
                    session.task.state.validation_courtesy = True

                session.task.state.validation_page += 3
                if num_req <= session.task.state.validation_page:
                    output.speech_text += self.SAFETY_WARNING
                    output.speech_text += WANT_TO_START
                    session.task.state.requirements_displayed = True
                else:
                    if session.headless:
                        output.idle_timeout = 1800
                        output.pause_interaction = True

        return session, output

    @staticmethod
    def __handle_help_screen(session: Session) -> None:
        if "_button" in session.turn[-1].user_request.interaction.text:
            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.append("InformIntent")
            raise PhaseChangeException()
        session.task.state.help_corner_active = False

    def __get_requirements_utterances(self, session: Session, amount=True) -> List[str]:
        """ Build list of utterances to convey task requirements to user.

        Calls the TaskManager service to retrieve a list of requirements for the
        currently selected TaskMap, returning them as a list of strings.

        Args:
            session (Session): the current Session object

        Returns:
            a list of strings (maybe empty)
        """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString())

        requirements_response: InfoResponse = self.task_manager.get_requirements(
            request)
        requirements_list: List[str] = []
        for requirement in requirements_response.unresolved_statements[:15]:
            if amount:
                requirements_list.append(requirement.amount + " " + requirement.body.replace(requirement.amount, ""))
            else:
                requirements_list.append(requirement.body)

        if len(requirements_list) > 0:
            pass
        else:
            logger.info("No requirements found")

        return requirements_list

    @staticmethod
    def verbal_progress(session: Session, num_req: int) -> str:
        """Perform initial formatting on a speech output string listing task requirements.

        The ``num_req`` parameter gives the total length of the list of requirements for the
        current task. This method uses this and ``session.task.state.validation_page`` to construct
        the initial part of the next speech output text. For example, if the ``validation_page`` is
        zero, the output will be a random selection from first_set_responses with the page number
        and type of requirements set appropriately.

        The actual requirements are appended to this in the ``step`` method.

        Args:
            session (Session): the current Session object
            num_req (int): number of requirements for the current TaskMap

        Returns:
            initial speech text string
        """
        speech_output = ""
        current_validation_page = session.task.state.validation_page

        # adds the correct suffix to a number, e.g. 1 => 1st, 13 => 13th, 22 => 22nd
        ordinals = lambda n: "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))

        # how many pages are needed to display the requirements in sets of 3?
        total_pages = num_req // 3
        if num_req % 3 != 0:
            total_pages += 1

        if session.domain == Session.Domain.COOKING:
            requirements_type = "ingredients"
        else:
            requirements_type = "things you'll need"
        if num_req <= 3:
            return speech_output

        if current_validation_page == 0:
            first_set_responses = [
                f"Alright, the {ordinals(current_validation_page + 1)} set of {requirements_type} are: ",
                f"Okay, for starters, you'll need: ",
                f"Awesome. To begin with, you'll have to get: "
            ]
            speech_output += random.choice(first_set_responses)
        elif (current_validation_page / 3) + 1 == total_pages:
            last_set_responses = [
                f"Finally, you'll need: ",
                f"The last set of {requirements_type} are: "
            ]
            speech_output += random.choice(last_set_responses)
        else:
            intermediate_set_responses = [
                f"The {ordinals((current_validation_page / 3) + 1)} set of {requirements_type} are: ",
                f"The next set of {requirements_type} are: "
            ]
            speech_output += random.choice(intermediate_set_responses)
        return speech_output

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the ValidationPolicy class.

        This policy is responsible for managing the transition from selecting a task to
        executing a task. It will call the PhaseIntentClassifier if necessary as a first
        step to assign an intent to the current turn. The remainder of the method deals with:

        - returning a response listing ingredients/tools required in response to a ShowRequirementsIntent
        - prompting the user to continue after displaying requirements
        - managing display/utterance of requirements when they need to be spread over multiple "pages"
        - raising a PhaseChangeException to redirect control to the ExecutionPolicy when the user wants to continue
        - routing control back to PlanningPolicy if a CancelIntent/NoIntent is encountered

        TODO more detail

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """
        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['CancelIntent']):
            route_to_planning(session)

        intent_request = IntentRequest()
        for turn in session.turn:
            intent_request.turns.append(turn)

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

        if session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:
            if "_button" in session.turn[-1].user_request.interaction.text and \
                    not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')
            self.__handle_help_screen(session)

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['CancelIntent', 'NoIntent', 'RestartIntent']):
            route_to_planning(session)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["SearchIntent"]) and \
                "replace" not in session.turn[-1].user_request.interaction.text.lower() and \
                "substitute" not in session.turn[-1].user_request.interaction.text.lower():
            route_to_domain(session)

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

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
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

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['QuestionIntent']) or \
                "replace" in session.turn[-1].user_request.interaction.text.lower() or \
                "substitute" in session.turn[-1].user_request.interaction.text.lower():
            session, output = self.qa_policy.step(session)
            user_utterance = session.turn[-1].user_request.interaction.text
            output = build_chat_screen(policy_output=output, user_utterance=user_utterance, session=session)
            set_source(output)
            return session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ChitChatIntent']):
            session, output = self.chitchat_policy.step(
                session
            )
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["StartTaskIntent"]):
            route_to_execution(session)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ShowRequirementsIntent"],
                                    utterances_list=['read ingredients', 'read tools and materials',
                                                     'read']):
            output = repeat_screen_response(session, output)
            requirements_list = self.__get_requirements_utterances(session)
            output.speech_text = f'You need: {", ".join(requirements_list[:-1])}'
            output.speech_text += f' and, finally, {requirements_list[-1]}'
            if not session.headless:
                if len(requirements_list) > 5:
                    output.speech_text += ". Wow, that were a lot of things!"
                output.speech_text += ". You can also see what you need on the screen, if that helps you. "

        elif session.task.state.requirements_displayed:
            if is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                      intents_list=["QuestionIntent"]) and \
                    any([prompt in session.turn[-2].agent_response.interaction.speech_text for prompt in
                         REPLACE_SUGGESTION]):
                if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                          intents_list=["YesIntent"]):
                    logger.info('We had a replacement suggestion!')
                    session = self.replacement_step_rewriter.adjust_step_texts(session)
                    session, output = self.build_ingredients_output(session, output)
                    options = [
                        "Cool! I just rewrote the recipe for you. Feel free to tell me if you want to replace other "
                        "ingredients. ",
                        "Awesome! I just changed the recipe for you. If you want to replace some other ingredients, "
                        "just let me know. ",
                        "Great! I changed the recipe for you. "
                    ]
                    output.speech_text = random.choice(options)
                    if not session.task.state.safety_warning_said:
                        output.speech_text += self.SAFETY_WARNING
                        session.task.state.safety_warning_said = True
                    output.speech_text += f" Anyway, say start to start the recipe! "
                elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                            intents_list=["NoIntent"]):
                    session, output = self.build_ingredients_output(session, output)
                    output.speech_text = f"Sure no worries, probably better to stick with the original. "
                    if not session.task.state.safety_warning_said:
                        output.speech_text += self.SAFETY_WARNING
                        session.task.state.safety_warning_said = True
                    output.speech_text += f"Shall we get started with '{session.task.taskmap.title}'?"
                else:
                    session, output = self.build_ingredients_output(session, output)
                    output.speech_text = ""
                    if not session.task.state.safety_warning_said:
                        output.speech_text += self.SAFETY_WARNING
                        session.task.state.safety_warning_said = True
                    output.speech_text += f"Do you want to get started with '{session.task.taskmap.title}'?"

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=["YesIntent"],
                                        utterances_list=['continue', 'start']):
                route_to_execution(session)

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                        intents_list=['PreviousIntent']):
                route_to_planning(session)

            else:
                session, output = self.build_ingredients_output(session, output)
                fallback = {
                    1: [
                        f"Shall we get started with '{session.task.taskmap.title}'? ",
                    ],
                    2: [
                        f"I'm having trouble understanding you. You can say yes if you "
                        f"would like to start {session.task.taskmap.title}, "
                        f"or say no if you don't.",

                    ]
                }

                if session.error_counter.no_match_counter < 2:
                    session.error_counter.no_match_counter += 1

                output.speech_text = self.SAFETY_WARNING
                output.speech_text += random.choice(fallback[session.error_counter.no_match_counter])

        else:
            session, output = self.build_ingredients_output(session, output)

        set_source(output)
        return session, output
