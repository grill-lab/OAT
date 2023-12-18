import os
import grpc

from policy.abstract_policy import AbstractPolicy
from task_manager_pb2 import InfoRequest, InfoResponse, Statement
from task_manager_pb2_grpc import TaskManagerStub
from taskmap_pb2 import OutputInteraction, Session, Task
from utils import is_in_user_interaction, logger, repeat_screen_response, set_source

from exceptions import PhaseChangeException
from typing import List, Optional, Tuple


class ConditionPolicy(AbstractPolicy):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.task_manager = TaskManagerStub(channel)

    def __get_conditions(self, session: Session) -> List[Statement]:
        """Get conditions from the current TaskMap.

        Args:
            session (Session): the current Session object

        Returns:
            List[Statement]: a list of condition statements
        """

        request: InfoRequest = InfoRequest()
        request.taskmap.ParseFromString(
            session.task.taskmap.SerializeToString()
        )
        request.state.ParseFromString(
            session.task.state.SerializeToString()
        )
        conditions_response: InfoResponse = self.task_manager.get_conditions(request)
        if conditions_response.unresolved_statements:
            logger.info(conditions_response.unresolved_statements)
        else:
            logger.info("NO CONDITIONS RETRIEVED")

        return conditions_response.unresolved_statements

    @staticmethod
    def __raise_phase_change(session: Session, phase: Task.TaskPhase):

        session.task.state.execution_ingredients_displayed = False
        # session.task.state.execution_tutorial_displayed = False
        session.task.phase = phase

        raise PhaseChangeException()

    def step(self, session: Session) -> Tuple[Optional[Session], Optional[OutputInteraction]]:
        """Step method for the ConditionPolicy class.

        This method expects to be called after a previous call to ``get_condition``. If
        no response is expected/required it hands back control to ExecutionPolicy by returning
        a (None, None) tuple.

        Otherwise it will generate a response and return an OutputInteraction based on the
        intent(s) in the current interaction, e.g. confirming a "Yes" or "No" response to a
        question that was asked.

        Args:
            session (Session): the current Session object

        Returns:
            tuple(None, None), or tuple(updated Session, OutputInteraction)
        """
        output: OutputInteraction = OutputInteraction()

        if is_in_user_interaction(session.turn[-1].user_request.interaction,
                                        intents_list=['StopIntent']):
            self.__raise_phase_change(session, phase=Task.TaskPhase.CLOSING)

        if session.task.state.condition_id_eval != "":
            # We have already asked a condition to the user so we want to judge the user response
            if is_in_user_interaction(session.turn[-1].user_request.interaction,
                                      intents_list=['YesIntent']):
                session.task.state.true_statements_ids.append(session.task.state.condition_id_eval)
                output.speech_text += "Ok, got it! Are you ready to get started? "
            elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                        intents_list=['NoIntent']):
                session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                output.speech_text += "Ok, that's fine! Ready to continue? "
            else:
                # Default case
                statements: List[Statement] = self.__get_conditions(session)
                condition_id: str = session.task.state.condition_id_eval
                eval_statement = [statement for statement in statements if statement.node_id == condition_id][0]

                if eval_statement.default.lower() == 'yes':
                    session.task.state.true_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a Yes, since it is the better option! "
                elif eval_statement.default.lower() == 'no':
                    session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a No, since it is the better option! "
                else:
                    logger.warning(f"WARNING: Default condition value does not match the yes/no "
                                   f"expected value. It got instead {eval_statement.default}.")

                    # For not matching Yes/No values we consider the default action to be No
                    session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a No, since it is the better option! "

            session.task.state.condition_id_eval = ""
            output = repeat_screen_response(session, output)

            remaining_condition = self.get_condition(session)
            if remaining_condition is not None:
                output.speech_text += remaining_condition

            if not session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True

            set_source(output)
            return session, output
        else:
            return None, None

    def get_condition(self, session: Session) -> Optional[str]:
        """Returns a Condition Request if it is available from the graph.

        If more than 1 condition is present we just take the first one.

        Args:
            session (Session): the current Session object

        Returns:
            Optional[str]: a condition request, if available, otherwise None
        """
        statements = self.__get_conditions(session)

        if session.task.state.condition_id_eval == "" and len(statements) > 0:
            # We have conditions that need to be resolved but we don't have asked any yet

            target_condition: Statement = statements[0]
            session.task.state.condition_id_eval = target_condition.node_id

            return target_condition.body
        else:
            return None
