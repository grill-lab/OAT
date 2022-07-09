from taskmap_pb2 import Session, OutputInteraction, ScreenInteraction, Task
from .abstract_intent_handler import AbstractIntentHandler
from utils import repeat_screen_response
from random import sample


class HelpHandler(AbstractIntentHandler):

    @property
    def caught_intents(self):
        return ["AMAZON.HelpIntent", "ConfusedIntent"]

    def step(self, session: Session) -> (Session, OutputInteraction):

        output = OutputInteraction()
        output.idle_timeout = 10
        tutorial_list = []

        phase = session.task.phase

        if phase == Task.TaskPhase.DOMAIN:
            tutorial_list.append(f"I can help you cook or do some home improvement. You can tell me what you want to "
                                 f"do and ask me questions. When you have chosen a task, just use Next and "
                                 f"Previous to navigate the Task Instructions, or ask me questions about it.")

        elif phase == Task.TaskPhase.PLANNING:
            if session.task.taskmap.taskmap_id != '':
                PROMPT_1 = f"This is the summary of {session.task.taskmap.title}. If you want to continue, "\
                           f"just say 'start'. You can go back to the search results by saying 'cancel'"
                PROMPT_2 = f'What do you think of {session.task.taskmap.title}? If you want to start, just say ' \
                           f'"start". By saying "restart", you can start a new search.'
                PROMPT_3 = f"You are currently previewing {session.task.taskmap.title}. " \
                           f"If you want to continue this task, just say 'start' or go back to the search results " \
                           f"by saying 'cancel'"
                tutorial_list.extend([PROMPT_1, PROMPT_2, PROMPT_3])
            else:
                TUTORIAL1 = 'You can start a new search by saying "cancel" or "restart".'

                TUTORIAL2_UI = 'You can select one of the results by saying its name, ' \
                               ' or clicking the image on the screen.'
                TUTORIAL2_HL = 'You can select one of the results by saying ' \
                               'the name of the result'

                if session.headless:
                    tutorial_list = [TUTORIAL1, TUTORIAL2_HL]
                else:
                    tutorial_list = [TUTORIAL1, TUTORIAL2_UI]

        elif phase == Task.TaskPhase.VALIDATING:
            if session.headless:
                tutorial_list.append('You can navigate through the requirements by saying next or previous, or say '
                                     'cancel to go back to the search results.')
            else:
                PROMPT_1 = f'You can see what you need for {session.task.taskmap.title} on the screen.'\
                           f' Say "start" if you want to see the steps, "cancel" if you would like to go'\
                           f' back to the search results.'
                PROMPT_2 = f'Would you like to continue with {session.task.taskmap.title}? If yes, say '\
                           f'"start" to get started, else say "restart" to go back to the search results.'
                tutorial_list.extend([PROMPT_1, PROMPT_2])

        elif phase == Task.TaskPhase.EXECUTING:
            TUTORIAL1 = 'You can navigate through the steps by saying "Next", "Previous" or "Repeat", ' \
                        'or you can go back to the search results by saying "cancel".'

            TUTORIAL2 = 'You can ask any question about the requirements and steps if you have any doubts. ' \
                        'I can also repeat the last instruction if you say Repeat.'

            TUTORIAL3 = 'Just invoke me again and I will be back to help you with your task.'

            TUTORIAL4_SCREEN = 'You can say "more details" to see more information about the step, if ' \
                               'available. By saying "show requirements" you can see the things you need again'

            if session.headless:
                tutorial_list.extend([TUTORIAL1, TUTORIAL2])
            else:
                tutorial_list.extend([TUTORIAL1, TUTORIAL2, TUTORIAL3, TUTORIAL4_SCREEN])

            if not session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True

        chosen_tutorial = sample(tutorial_list, 1)[0]
        output.speech_text = chosen_tutorial
        output = repeat_screen_response(session, output)

        return session, output
