import os
import random
import grpc

from typing import Optional, Tuple

from policy.abstract_policy import AbstractPolicy
from analytics.general.safety_parser import SafetyParser
from task_manager_pb2 import ExtraList, TMRequest
from task_manager_pb2_grpc import TaskManagerStub
from taskmap_pb2 import ExtraInfo, OutputInteraction, Session
from utils import (
    is_in_user_interaction, logger, repeat_screen_response, set_source,
    BOT_THINKS_HE_IS_FUNNY, CONTINUE_PROMPTS,
    EXPERTS_THINK_PROMPT, JOKE_INTRO_PROMPT
)


class ExtraInfoPolicy(AbstractPolicy):

    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.task_manager = TaskManagerStub(channel)
        self.safety_parser = SafetyParser()
        self.extra_info = None

    def __get_extra_information(self, session: Session) -> Optional[Tuple[ExtraList, str]]:
        """Returns extra info items for the current step, if available.

        Args:
            session (Session): the current Session object

        Returns:
            ExtraList: a list of ExtraInfo objects
        """
        request = TMRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString()
        )
        request.state.ParseFromString(
            session.task.state.SerializeToString()
        )

        step = self.task_manager.get_step(request)
        extra_info_list = step.screen.extra_information

        if len(extra_info_list) > 0:
            weights = [
                10 if extra_info.type in {ExtraInfo.InfoType.JOKE, ExtraInfo.InfoType.FUNFACT}
                else 20 if extra_info.type in {ExtraInfo.InfoType.QUESTION} else 4
                for extra_info in extra_info_list
            ]
            extra_info = random.choices(extra_info_list, weights=weights)[0]

            if False in self.safety_parser.check_utterance(extra_info.text):
                logger.info(f"Cannot retrieve {extra_info.text}, safety check failed")
                return None, ""

            if not session.headless:
                if len(step.screen.image_list) > 1:
                    logger.info('WE HAVE A JOKE IMAGE')
                    return extra_info, step.screen.image_list[-1].path

            return extra_info, ""

        return None, ""

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the ExtraInfoPolicy class.
        If the current turn contains a NoIntent, this will generate a simple
        response instructing the user to continue with the task. If a
        YesIntent is found instead, it will check the type of extra information
        available (this is retrieved and stored by a previous call to
        ``get_extra_information``), and use JOKE/PUN text as the speech text
        response, appending a random choice of continuation prompt after it.
        Args:
            session (Session): the current Session object
        Returns:
            tuple(updated Session, OutputInteraction)
        """
        output: OutputInteraction = OutputInteraction()
        if self.extra_info.type not in {ExtraInfo.InfoType.JOKE, ExtraInfo.InfoType.PUN}:
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=["YesIntent", "NoIntent"]):
                output.speech_text = self.extra_info.text
                output.speech_text += random.choice(CONTINUE_PROMPTS)
        else:
            output = repeat_screen_response(session, output)
            session.task.state.extra_info_unresolved = False
            if self.extra_info is not None:
                session.task.state.true_statements_ids.append(self.extra_info.unique_id)
            self.extra_info = None

        set_source(output)
        return session, output

    def get_extra_information(self, session: Session) -> Tuple[str, str]:
        """Retrieve extra info items for the current step, if available.

        This method calls ``__get_extra_information`` to retrieve any available
        ExtraInfo items, and stores them in ``self.extra_info``. It then checks
        the type of the item (fact, joke, pun, tip, ...) and constructs a speech
        text string based on that in addition to updating the session state.

        Args:
            session (Session): the current Session object

        Returns:
            str: a speech text string, empty if no extra info available
        """
        self.extra_info, image_url = self.__get_extra_information(session)
        speech_text = ""
        if self.extra_info:
            if self.extra_info.type == ExtraInfo.InfoType.QUESTION and not session.task.state.question_uttered:
                speech_text += self.extra_info.text
                session.task.state.question_uttered = True
            elif self.extra_info.type in {ExtraInfo.InfoType.JOKE, ExtraInfo.InfoType.PUN} and not session.task.state.joke_uttered:
                speech_text += random.choice(JOKE_INTRO_PROMPT).format(self.extra_info.keyword)
                speech_text += self.extra_info.text
                speech_text += random.choice(BOT_THINKS_HE_IS_FUNNY)
                session.task.state.joke_uttered = True
            elif self.extra_info.type == ExtraInfo.InfoType.TIP or self.extra_info.type == ExtraInfo.InfoType.FUNFACT  and not session.task.state.tip_uttered:
                speech_text = random.choice(EXPERTS_THINK_PROMPT)
                speech_text += self.extra_info.text
                speech_text += random.choice(CONTINUE_PROMPTS)
                session.task.state.tip_uttered = True
        else:
            return speech_text, image_url

        return speech_text, image_url
