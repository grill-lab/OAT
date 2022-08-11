import os
import json
import grpc
import random
import re

from policy.abstract_policy import AbstractPolicy
from policy.qa_policy import DefaultPolicy as DefaultQAPolicy
from taskmap_pb2 import Session, OutputInteraction, Task, Video, ScreenInteraction, Image

from task_manager_pb2_grpc import TaskManagerStub
from task_manager_pb2 import TMRequest, TMResponse, InfoRequest, InfoResponse, ExtraList

from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from phase_intent_classifier_pb2 import IntentRequest, IntentClassification

from video_searcher_pb2 import VideoQuery, TaskStep
from video_searcher_pb2_grpc import VideoSearcherStub, ActionClassifierStub

from image_searcher_pb2 import ImageRequest
from image_searcher_pb2_grpc import ImageSearcherStub

from utils import logger, is_in_user_interaction, consume_intents, repeat_screen_response, show_ingredients_screen, \
                    RIND_FALLBACK_RESPONSE, EXECUTION_NO_CANCEL, build_video_button, CHIT_CHAT, ASR_ERROR, \
                    format_requirements
from exceptions import PhaseChangeException
from .condition_policy import ConditionPolicy
from .actions import perform_action
from .extra_info_policy import ExtraInfoPolicy

from typing import List


class ExecutionPolicy(AbstractPolicy):
    def __init__(self) -> None:
        # with open("policy/domain_policy/rulebook.json") as json_rulebook:
        #     self.rulebook = json.load(json_rulebook)

        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])

        # self.intent_classifier = IntentClassifierStub(channel)
        self.task_manager = TaskManagerStub(channel)
        self.phase_intent_classifier = PhaseIntentClassifierStub(neural_channel)
        # self.video_searcher = VideoSearcherStub(neural_channel)
        self.action_classifier = ActionClassifierStub(channel)
        self.qa_policy = DefaultQAPolicy()

        self.condition_policy = ConditionPolicy()
        self.extra_info_policy = ExtraInfoPolicy()
        self.image_searcher = ImageSearcherStub(neural_channel)

    def __check_and_perform_actions(self, session: Session, output: OutputInteraction) -> None:
        """
        Method that checks if there are actions to perform
        """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString()
        )
        request.state.ParseFromString(
            session.task.state.SerializeToString()
        )
        actions_response: InfoResponse = self.task_manager.get_actions(request)

        if actions_response.unresolved_statements:
            logger.info(f"Found {len(actions_response.unresolved_statements)} Actions to perform!!")
            for action_statement in actions_response.unresolved_statements:
                perform_action(session, output, action_statement)

    def __get_requirements_utterances(self, session: Session, local: bool) -> List[str]:
        """ Build list of utterances to to convey task requirements to user. """
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString())

        if local:
            request.local = local
            request.state.ParseFromString(session.task.state.SerializeToString())

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
    def __raise_phase_change(session: Session, phase: Task.TaskPhase):

        session.task.state.execution_ingredients_displayed = False
        # session.task.state.execution_tutorial_displayed = False
        session.task.phase = phase

        raise PhaseChangeException()

    # def __retrieve_video(self, session: Session) -> Video:
    #     # retrieve current step text
    #     request = TMRequest()
    #     request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
    #     request.state.ParseFromString(session.task.state.SerializeToString())
    #
    #     step: TaskStep = TaskStep()
    #     step_output = self.task_manager.get_step(request)
    #     step.step_text = step_output.speech_text
    #     video_message: Video = Video()
    #
    #     query: VideoQuery = VideoQuery()
    #     if step_output.screen.caption_query == '':
    #         action_classification = self.action_classifier.classify_action_step(step)
    #         logger.info(f'Step contains an action: {action_classification.is_action}')
    #
    #         if action_classification.is_action:
    #             query.text = random.choice(action_classification.methods)
    #             query.top_k = 10
    #     else:
    #         query.text = step_output.screen.caption_query
    #         query.top_k = 10
    #
    #     if query.text != "":
    #         best_video_match = self.video_searcher.search_video(query)
    #
    #         if best_video_match.title != "":
    #             logger.info(f'Found a video: {best_video_match.title}')
    #             video_message.title = best_video_match.title
    #             video_message.hosted_mp4 = f"https://sophie-video-project.s3.amazonaws.com/{best_video_match.hosted_mp4}"
    #             video_message.doc_id = best_video_match.doc_id
    #
    #     return video_message
    
    def __retrieve_image(self, session: Session) -> Image:
        request = TMRequest()
        request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
        request.state.ParseFromString(session.task.state.SerializeToString())

        # get step
        step: TaskStep = TaskStep()
        step_output = self.task_manager.get_step(request)
        step.step_text = step_output.speech_text
        image: Image = Image()
        image.path = session.task.taskmap.thumbnail_url

        if step_output.screen.caption_query == '':
            image_request = ImageRequest()
            image_request.query = step_output.screen.caption_query
            image_request.k = 1

            retrieved_image = self.image_searcher.search_image(image_request)
            if retrieved_image.path != "":
                image.MergeFrom(retrieved_image)
                logger.info(image)
            else:
                image.path = session.task.taskmap.thumbnail_url
        
        return image

    def step(self, session: Session) -> (Session, OutputInteraction):

        if len(session.turn[-1].user_request.interaction.intents) == 0:
            intent_request = IntentRequest()
            for turn in session.turn:
                intent_request.turns.append(turn)

            output: OutputInteraction = OutputInteraction()

            intent_classification = (
                self.phase_intent_classifier.classify_intent(intent_request)
            )
            session.turn[-1].user_request.interaction.params.append(intent_classification.attributes.raw)

            translation_dict = {
                "select": "GoToIntent",
                "cancel": "CancelIntent",
                "restart": "CancelIntent",
                "search": "CancelIntent",
                "yes": "YesIntent",
                "no": "NoIntent",
                "repeat": "RepeatIntent",
                "confused": "ConfusedIntent",
                "show_more_results": "DetailsIntent",
                "show_requirements": "ShowRequirementsIntent",
                "show_more_details": "DetailsIntent",
                "next": "NextIntent",
                "previous": "PreviousIntent",
                "stop": "StopIntent",
                "chit_chat": "ChitChatIntent",
                "set_timer": "createTimerIntent",
                "stop_timer": "deleteTimerIntent",
                "pause_timer": "pauseTimerIntent",
                "resume_timer": "resumeTimerIntent",
                "show_timers": "showTimerIntent",
                "ASR_error": "ASRErrorIntent",
                "answer_question": "QuestionIntent",
                "inform_capabilities": "ConfusedIntent",
                "step_select": "GoToIntent",
                "pause": 'PauseIntent',
                "start_task": 'YesIntent',
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
        condition_text = None

        out_session, output = self.condition_policy.step(session)
        if out_session is not None and output is not None:
            # Check for actions to be perfomed
            self.__check_and_perform_actions(session, output)
            return out_session, output

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=[], utterances_list=['play video', 'click the video button']):
            output = OutputInteraction()
            if session.headless:
                output.speech_text = "Sorry, we cannot play a video without a screen. Why don't you continue" \
                                     "with the recipe?"
            else:

                previous_agent_response = session.turn[-2].agent_response.interaction
                if previous_agent_response.screen.video.title != "":
                    output.screen.video.MergeFrom(
                        previous_agent_response.screen.video
                    )
                    output.screen.format = ScreenInteraction.ScreenFormat.VIDEO
                    output.idle_timeout = 1800
                    output.pause_interaction = True
                    output.speech_text = "Playing video now..."
                else:
                    # we didn't find a relevant video to play
                    output: OutputInteraction = repeat_screen_response(session, output)
                    output.speech_text = "Unfortunately, I don't have a useful video for this step."

            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["ConfusedIntent",
                                                  "createTimerIntent",
                                                  "pauseTimerIntent",
                                                  "deleteTimerIntent",
                                                  "resumeTimerIntent",
                                                  "showTimerIntent"]):
            raise PhaseChangeException()

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["YesIntent", "NoIntent"]) and session.task.state.extra_info_unresolved:
            _, output = self.extra_info_policy.step(session)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=['StopIntent', 'AMAZON.StopIntent']):
            self.__raise_phase_change(session, phase=Task.TaskPhase.CLOSING)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ChitChatIntent', 'QuestionIntent']):
            _, output = self.qa_policy.step(
                session
            )
            output = repeat_screen_response(session, output)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=['ASRErrorIntent']):
            user_utterance = session.turn[-1].user_request.interaction.text
            output.speech_text = random.choice(ASR_ERROR).format(user_utterance)
            output = repeat_screen_response(session, output)
            return session, output

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["CancelIntent", "AMAZON.CancelIntent"]):

            consume_intents(session.turn[-1].user_request.interaction,
                            intents_list=["CancelIntent", "AMAZON.CancelIntent"])
            
            output = OutputInteraction()
            
            output.speech_text = random.choice(EXECUTION_NO_CANCEL)
            output: OutputInteraction = repeat_screen_response(session, output)

            return session, output

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['PauseIntent']):
            output = OutputInteraction()
            output.idle_timeout = 1800
            output.pause_interaction = True
            if session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True
                alexa_paused = [
                    "I have paused the conversation",
                    "conversation paused",
                    "paused for now, wake me if you need me!"
                ]
                output.speech_text = random.sample(alexa_paused, 1)[0]
            else:
                output.speech_text = "I have paused the conversation. " \
                                     "If you want to speak to me again just wake me."

            output: OutputInteraction = repeat_screen_response(session, output)

            return session, output

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['ShowRequirementsIntent'],
                                    utterances_list=['show me the ingredients']):
            requirements_list = self.__get_requirements_utterances(session, local=False)

            output: OutputInteraction = OutputInteraction()
            if not session.headless:
                output: OutputInteraction = show_ingredients_screen(session, requirements_list, output)
                # add start with task button
                output.screen.buttons.append("Continue")
                output.screen.on_click_list.append("repeat")

            output.speech_text = ''
            if requirements_list == []:
                output.speech_text += "This task has no requirements. You can say 'next' to keep going," \
                                      "or say 'repeat' to hear the step again."
            else:
                if session.headless:
                    output.speech_text = f'For {session.task.taskmap.title}, you need: {". ".join(requirements_list)}. '
                else:
                    output.speech_text = f'Here are the task requirements for {session.task.taskmap.title}. '

                output.speech_text += 'You can navigate back to the task by saying "Go back"'

            session.task.state.execution_ingredients_displayed = True
            return session, output

        elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                    intents_list=['DetailsIntent'],
                                    utterances_list=['more details', 'details', 'show me more']):
            request = TMRequest()
            request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
            request.state.ParseFromString(session.task.state.SerializeToString())
            request.taskmap.headless = session.headless

            output: OutputInteraction = self.task_manager.more_details(request)

            if not session.headless:
                # search for video
                #found_video: Video = self.retrieve_video(session)
                previous_agent_response = session.turn[-2].agent_response.interaction
                if previous_agent_response.screen.video.title != "":
                    output.screen.video.MergeFrom(previous_agent_response.screen.video)
                    speech_text, screen = build_video_button(output, output.screen.video)
                    output.screen.ParseFromString(screen.SerializeToString())
                    output.speech_text += speech_text


            output.idle_timeout = 1800
            output.pause_interaction = True
            return session, output

        else:

            request = TMRequest()
            request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
            request.state.ParseFromString(session.task.state.SerializeToString())
            request.taskmap.headless = session.headless

            try:
                if session.task.state.execution_ingredients_displayed:
                    session.task.state.execution_ingredients_displayed = False
                    request.state.execution_ingredients_displayed = False
                    tm_response: TMResponse = self.task_manager.repeat(request)

                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['PreviousIntent']):
                    tm_response: TMResponse = self.task_manager.previous(request)
                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['RepeatIntent']):
                    tm_response: TMResponse = self.task_manager.repeat(request)
                elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                            intents_list=['GoToIntent']):
                    request.attribute = intent_classification.attributes.step
                    tm_response: TMResponse = self.task_manager.go_to(request)

                else:
                    tm_response: TMResponse = self.task_manager.next(request)

            except grpc.RpcError as e:
                if "EndOfExecutionException" in e.details():
                    logger.warning(
                        "Exception on getting the next step, "
                        "we reached the end of execution"
                    )

                    # This will mean that most likely we don't have any more steps to execute
                    self.__raise_phase_change(session, phase=Task.TaskPhase.CLOSING)

                else:
                    logger.exception("Unknown error ", exc_info=e)
                    raise e

            session.task.state.ParseFromString(
                tm_response.updated_state.SerializeToString()
            )
            output = tm_response.interaction

            # check for images
            if len(output.screen.image_list) == 0:
                image = self.__retrieve_image(session)
                output.screen.image_list.append(image)

            requirements_list = self.__get_requirements_utterances(session, local=True)
            if requirements_list:
                for req in requirements_list:
                    output.screen.requirements.append(req)

            condition_text = self.condition_policy.get_condition(session)
            if condition_text is not None:
                output.speech_text += " " + condition_text

            # Video result Mocking
            if not session.headless and os.environ.get("MOCK_VIDEO") == "True":
                found_video: Video = Video()

                found_video.title = "Mock Video Result"
                found_video.hosted_mp4 = f"https://sophie-video-project.s3.amazonaws.com/_2d7CpbxycM.mp4"
                found_video.doc_id = ""
                output.screen.video.MergeFrom(found_video)
                speech_text, screen = build_video_button(output, found_video)
                output.screen.ParseFromString(screen.SerializeToString())
                output.speech_text += speech_text

            #     found_video: Video = self.__retrieve_video(session)
            #
            #     if found_video.title != "":
            #         logger.info(f'FOUND VIDEO: {found_video.title}')
            #         output.screen.video.MergeFrom(found_video)
            #         speech_text, screen = build_video_button(output, found_video)
            #         output.screen.ParseFromString(screen.SerializeToString())
            #         output.speech_text += speech_text

            if output.screen.hint_text != "":
                hint_text_options = [output.screen.hint_text]
            else:
                hint_text_options = []

            hint_text_options.append('Hint: I can answer questions')
            hint_text_options.append('Hint: Try asking a question')
            hint_text_options.append('Hint: Ask for substitutions')
            speech_req = "ingredients" if session.domain == Session.Domain.COOKING else "tools or materials"
            hint_text_options.append(f'Hint: Ask about specific {speech_req}')

            output.screen.hint_text = random.choice(hint_text_options)
            logger.info(f'HINT TEXT: {output.screen.hint_text}')

            if condition_text is None and output.screen.video.title == "" and session.task.state.index_to_next > 1:
                speech_length =  len(re.findall(r'\w+', output.speech_text))
                lower_bound = 6
                upper_bound = 30
                if (speech_length < lower_bound) or \
                    (speech_length >= lower_bound and speech_length < upper_bound and random.uniform(0, 1) < 0.4):
                    extra_info_text = self.extra_info_policy.get_extra_information(session)
                    output.speech_text += extra_info_text

            if not session.task.state.execution_tutorial_displayed:
                session.task.state.execution_tutorial_displayed = True
                task_type : str = "recipe" if session.domain == Session.Domain.COOKING else "task"
                if not session.headless:
                    output.speech_text = f'Got it. So you\'re aware, you can ask me to repeat, go back, or say the next step. ' \
                                         f'If you\'d like, I can also give you more details about a step, or remind you of the things ' \
                                         f'you\'ll need for this {task_type}. ' \
                                         f'So, for ' + output.speech_text
                else:
                    output.speech_text = f"Let's get started with {session.task.taskmap.title}. " \
                                        f"So you're aware, I'll say the steps one at a time, and, " \
                                        f"you can ask me to repeat, go back, or say the next step. " \
                                        f"If you'd like, I can also give you more details about a step, or remind you of what " \
                                        f"you'll need to complete the {task_type}. " \
                                        f'So, for ' + output.speech_text

        output.idle_timeout = 10
        if not session.headless and condition_text is None:
            output.idle_timeout = 1800
            output.pause_interaction = True

        # Tutorial utterances can be inserted in the re-prompted speech, that is read after
        # a few seconds of silence from the user. This achieves that if he does not know what to do,
        # we guide him on the operations that can be done during execution

        TUTORIAL1 = 'You can navigate through the steps by saying "Next", "Previous" or "Repeat", ' \
                    'or you can go back to the search results by saying "cancel".'

        TUTORIAL2 = 'You can ask any question about the requirements and steps if you have any doubts. ' \
                    'I can also repeat the last instruction if you say "Repeat".'

        tutorial_list = [TUTORIAL1, TUTORIAL2]

        chosen_tutorial = random.sample(tutorial_list, 1)[0]
        output.reprompt = chosen_tutorial

        self.__check_and_perform_actions(session, output)
        return session, output