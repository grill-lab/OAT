import os
import random

from policy.abstract_policy import AbstractPolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import IntentRequest, IntentClassification

from taskmap_pb2 import Session, OutputInteraction, Task, ScreenInteraction, Image, InputInteraction, SessionState
from exceptions import PhaseChangeException

from utils import logger, get_credit_from_taskmap, is_in_user_interaction, \
    repeat_screen_response, screen_summary_taskmap, consume_intents, show_ingredients_screen, format_author_headless, \
    RIND_FALLBACK_RESPONSE, CHIT_CHAT, ASR_ERROR
import grpc
from typing import List

from task_manager_pb2_grpc import TaskManagerStub
from task_manager_pb2 import InfoRequest, InfoResponse


def route_to_planning(session):
    consume_intents(session.turn[-1].user_request.interaction,
                    intents_list=["CancelIntent", "AMAZON.CancelIntent", "NoIntent", "PreviousIntent"])
    session.task.phase = Task.TaskPhase.PLANNING
    session.task.state.requirements_displayed = False
    session.task.state.validation_courtesy = False
    session.task.state.validation_page = 0
    session.task_selection.results_page = 0
    session.task.taskmap.Clear()
    raise PhaseChangeException()

def route_to_execution(session):
    session.task.phase = Task.TaskPhase.EXECUTING
    session.task.state.requirements_displayed = False
    session.task.state.validation_page = 0
    session.error_counter.no_match_counter = 0
    raise PhaseChangeException()    


class ValidationPolicy(AbstractPolicy):

    # WANT_TO_START = 'Say cancel if you want to go back to the search results. Do you want to start?'
    WANT_TO_START = 'Do you want to start?'
    SAFETY_WARNING = 'Before we get started, please be careful when using any tools or equipment. ' \
                     'Remember, safety first! '

    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        neural_channel = grpc.insecure_channel(
            os.environ["NEURAL_FUNCTIONALITIES_URL"])

        self.task_manager: TaskManagerStub = TaskManagerStub(channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(
            neural_channel)
        self.qa_policy = DefaultQAPolicy()

    def __get_requirements_utterances(self, session: Session) -> List[str]:
        """ Build list of utterances to to convey task requirements to user. """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString())

        requirements_response: InfoResponse = self.task_manager.get_requirements(
            request)
        requirements_list: List[str] = []
        for requirement in requirements_response.unresolved_statements:
            requirements_list.append(requirement.body)

        if requirements_list:
            logger.info(f'Requirements: {requirements_list}')
        else:
            logger.info("No requirements found")

        return requirements_list

    @staticmethod
    def verbal_progress(session: Session, num_req):
        speech_output = ""
        current_validation_page = session.task.state.validation_page

        ordinals = lambda n: "%d%s"%(n,{1:"st",2:"nd",3:"rd"}.get(n if n<20 else n%10,"th"))

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

    def step(self, session: Session) -> (Session, OutputInteraction):

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['AMAZON.CancelIntent']):
            route_to_planning(session)

        intent_request = IntentRequest()
        for turn in session.turn:
            intent_request.turns.append(turn)

        grillbot_last_response = session.turn[-2].agent_response.interaction
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

            intent_translation = translation_dict.get(intent_classification.classification)
            if intent_translation:
                session.turn[-1].user_request.interaction.intents.append(
                    intent_translation
                )
            else:
                output.speech_text = random.choice(RIND_FALLBACK_RESPONSE)
                output = repeat_screen_response(session, output)
                return session, output

        logger.info(f'INTENTS: {session.turn[-1].user_request.interaction.intents}')

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['CancelIntent', 'NoIntent', 'RestartIntent']):
            route_to_planning(session)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ConfusedIntent",
                                                  "createTimerIntent",
                                                  "pauseTimerIntent",
                                                  "deleteTimerIntent",
                                                  "resumeTimerIntent",
                                                  "showTimerIntent"
                                                  ]):
            raise PhaseChangeException()

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
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

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['StopIntent', 'AMAZON.StopIntent']):
            session.task.phase = Task.TaskPhase.CLOSING
            session.task.state.requirements_displayed = False
            session.task.state.validation_page = 0
            session.task.taskmap.Clear()
            raise PhaseChangeException()
        
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

            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=["YesIntent"],
                                      utterances_list=['continue', 'start']):
                route_to_execution(session)

            elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=['PreviousIntent']):
                route_to_planning(session)

            else:
                fallback = {
                    1 : [
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

                output.screen.ParseFromString(
                    grillbot_last_response.screen.SerializeToString())
                output.speech_text = random.choice(fallback[session.error_counter.no_match_counter])

        else:
            # taskmap_credit = get_credit_from_taskmap(session.task.taskmap)
            requirements_list = self.__get_requirements_utterances(session)

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
                else:
                    # unsure if we should say the title of task over and over
                    pass
                    # output.speech_text += f"So, you chose {session.task.taskmap.title} "

                    # # Add credit if we know source url.
                    # if session.task.taskmap.author != "":
                    #     output.speech_text += f'by {format_author_headless(session.task.taskmap.author)}'
                    # if taskmap_credit != "":
                    #     output.speech_text += f', brought to you by {taskmap_credit}. '
                output.speech_text += 'Speaking of, this task has no requirements! but, ' + \
                    self.SAFETY_WARNING + self.WANT_TO_START

            else:
                if not session.headless:

                    output.speech_text = "Before we get started, please be careful when using " \
                                         "any tools or equipment. "

                    ingredients_output: OutputInteraction = show_ingredients_screen(session, requirements_list, output)
                    # add start with task button
                    speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools and materials"
                    ingredients_output.screen.buttons.append(f"Read")
                    ingredients_output.screen.on_click_list.append(f"show the {speech_req}")
                    ingredients_output.screen.buttons.append("Start")
                    ingredients_output.screen.on_click_list.append("Start")
                    ingredients_output.screen.hint_text = 'Start'
                    output.screen.ParseFromString(ingredients_output.screen.SerializeToString())

                    output.speech_text += self.WANT_TO_START
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
                    subset = [f"{idx+1}. {item}" if str(idx + 1) not in item else f"{item}" for idx, item in enumerate(subset)]
                    output.speech_text += self.verbal_progress(session, len(requirements_list))
                    if len(subset) > 1:
                        output.speech_text += '. '.join(subset[:-1]) + '. ' + ' And, ' + subset[-1]  + '. '
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
                        output.speech_text += self.WANT_TO_START
                        session.task.state.requirements_displayed = True
                    else:
                        if session.headless:
                            output.idle_timeout = 1800
                            output.pause_interaction = True

        return session, output
