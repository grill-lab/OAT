import os
import random
from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, OutputInteraction, Task, Image, ScreenInteraction, Transcript
from utils import close_session
from task_manager_pb2_grpc import TaskManagerStub
from task_manager_pb2 import TMRequest, TMResponse
import grpc
from utils import COOKING_FAREWELL


class FarewellPolicy(AbstractPolicy):

    def __init__(self):

        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.task_manager = TaskManagerStub(channel=channel)

    @staticmethod
    def __stop_intent(session: Session) -> bool:
        last_interaction = session.turn[-1].user_request.interaction
        return "StopIntent" in last_interaction.intents or \
               "AMAZON.StopIntent" in last_interaction.intents or \
               "stop" == last_interaction.text.lower()

    def __set_transcript(self, session, output):
        request: TMRequest = TMRequest()
        request.taskmap.ParseFromString(session.task.taskmap.SerializeToString())
        request.state.ParseFromString(session.task.state.SerializeToString())
        # Populating Transcript when ending the interaction
        transcript: Transcript = self.task_manager.get_transcript(request)
        output.transcript.ParseFromString(transcript.SerializeToString())
        session.task.state.transcript_sent = True
        return session, output

    def step(self, session: Session) -> (Session, OutputInteraction):
        # Logic is that we want to ask if user as completed task if we don't have to stop abruptly
        output: OutputInteraction = OutputInteraction()

        # # -- stop intent --
        # if session.task.taskmap.title != '' and self.__stop_intent(session):
        #     session, output = self.__set_transcript(session, output)
        #     session, output = close_session(session, output)

        # In this case we have reached the end of Execution
        if session.task.phase == Task.TaskPhase.CLOSING and \
                session.task.taskmap.title != '' and \
                not self.__stop_intent(session):

            if not session.headless:
                output.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
                output.screen.headline = "That's all folks!"
                output.screen.paragraphs.append(f"You just did: {session.task.taskmap.title}")
                output.screen.hint_text = 'Stop'
                image: Image = output.screen.image_list.add()
                image.path = session.task.taskmap.thumbnail_url

                output.screen.buttons.append("Complete")
                output.screen.on_click_list.append("complete")
                output.screen.hint_text = "Complete"

            # farewell_prompts = [
            #     f"You have completed {session.task.taskmap.title}, well done!",
            #     f"You just finished {session.task.taskmap.title}. You're awesome!",
            #     f"You just finished {session.task.taskmap.title}. Hope you had fun!"
            # ]

            DIY_FAREWELL = f"You have reached the end of your project, how awesome! " \
                           f"I hope you enjoyed my help with {session.task.taskmap.title} and you did it with a robot."

            if session.domain == Session.Domain.COOKING:
                output.speech_text = COOKING_FAREWELL
            else:
                output.speech_text = DIY_FAREWELL

            session.task.phase = Task.TaskPhase.EXECUTING
        else:
            session, output = self.__set_transcript(session, output)
            session, output = close_session(session, output)

        return session, output
