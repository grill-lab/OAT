from policy.abstract_policy import AbstractPolicy
import os
import grpc
import random

from taskmap_pb2 import Session, OutputInteraction, ExtraInfo
from task_manager_pb2 import InfoRequest, ExtraList
from task_manager_pb2_grpc import TaskManagerStub

from utils import logger, is_in_user_interaction, repeat_screen_response

class ExtraInfoPolicy(AbstractPolicy):

    def __init__(self) -> None:
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.task_manager = TaskManagerStub(channel)
        self.extra_info = None

    def __get_extra_information(self, session) -> ExtraList:
        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString()
        )
        request.state.ParseFromString(
            session.task.state.SerializeToString()
        )
        extra_info_list = self.task_manager.get_extra(request)
        logger.info(extra_info_list)

        if extra_info_list.extra_list:
            weights = [
                10 if extra_info.type in {ExtraInfo.InfoType.TIP, ExtraInfo.InfoType.FUNFACT} 
                else 8 if extra_info.type in {ExtraInfo.InfoType.QUESTION} else 4 
                for extra_info in extra_info_list.extra_list
            ]
            extra_info = random.choices(extra_info_list.extra_list, weights=weights)[0]
            return extra_info
        
        return None
    
    def step(self, session: Session) -> (Session, OutputInteraction):

        output: OutputInteraction = OutputInteraction()

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["YesIntent"]):
            output.speech_text = self.extra_info.text
            if self.extra_info.type in {ExtraInfo.InfoType.JOKE, ExtraInfo.InfoType.PUN}:
                output.speech_text += '<audio src="soundbank://soundlibrary/musical/amzn_sfx_drum_comedy_01"/>'
                PROMPTS = [" I'll let myself out. Anyhoo, let's continue by saying next. ",
                           "I'm totally kidding, I know this was a terrible joke. If you say next we can continue "
                           "with your task. ",
                           "just kidding, I'm having fun, hope you are too. Let's continue to get things done, "
                           "if you say next we can continue. "
                           ]
                output.speech_text += random.choice(PROMPTS)
                session.task.state.joke_uttered = True
            else:
                CONTINUE_PROMPTS = [' Anyway, just say next to continue. ',
                                    ' To continue, just say next. ',
                                    ' If you want to continue with the task, just say next. ']
                output.speech_text += random.choice(CONTINUE_PROMPTS)

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    intents_list=["NoIntent"]):
            output.speech_text = "That's okay. Just say next to keep going."
            
        output = repeat_screen_response(session, output)
        session.task.state.extra_info_unresolved = False
        session.task.state.true_statements_ids.append(self.extra_info.unique_id)
        self.extra_info = None
        return session, output
    
    def get_extra_information(self, session) -> str:

        self.extra_info = self.__get_extra_information(session)
        if self.extra_info:
            if self.extra_info.type == ExtraInfo.InfoType.FUNFACT:
                speech_text = " Do you want to hear something interesting? "
                session.task.state.extra_info_unresolved = True
            elif self.extra_info.type in {ExtraInfo.InfoType.JOKE, ExtraInfo.InfoType.PUN}:
                if not session.task.state.joke_uttered:
                    speech_text = " This reminds me of something funny. Wanna hear it? "
                    session.task.state.extra_info_unresolved = True
                else:
                    return ""
            elif self.extra_info.type == ExtraInfo.InfoType.TIP:
                PROMPTS = ['Did you know that', 'Experts agree that', 'Here is a fact for you:']
                CONTINUE_PROMPTS = [' Anyway, just say next to continue. ',
                                    ' To continue, just say next. ',
                                    ' If you want to continue with the task, just say next. ']
                speech_text = f" { random.choice(PROMPTS)} {self.extra_info.text} {random.choice(CONTINUE_PROMPTS)}"
                session.task.state.true_statements_ids.append(self.extra_info.unique_id)
                session.task.state.extra_info_unresolved = False
                self.extra_info = None
            else:
                speech_text = f" {self.extra_info.text} "
                session.task.state.true_statements_ids.append(self.extra_info.unique_id)
                session.task.state.extra_info_unresolved = False
                self.extra_info = None
        else:
            return ""
        
        return speech_text
