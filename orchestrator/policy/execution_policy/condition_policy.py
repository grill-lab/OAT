from policy.abstract_policy import AbstractPolicy
import os
import grpc
from typing import List, Optional

from taskmap_pb2 import Session, OutputInteraction
from task_manager_pb2 import InfoRequest, InfoResponse, Statement
from task_manager_pb2_grpc import TaskManagerStub

from utils import logger, is_in_user_interaction, repeat_screen_response


class ConditionPolicy(AbstractPolicy):

    def __init__(self):
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.task_manager = TaskManagerStub(channel)

    def __get_conditions(self, session) -> List[Statement]:

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

    def step(self, session: Session) -> (Session, OutputInteraction):
        output: OutputInteraction = OutputInteraction()

        if session.task.state.condition_id_eval != "":
            # We have already asked a condition to the user so we want to judge the user response
            if is_in_user_interaction(session.turn[-1].user_request.interaction,
                                      intents_list=['YesIntent']):
                session.task.state.true_statements_ids.append(session.task.state.condition_id_eval)
                output.speech_text += "Ok, got it!"
            elif is_in_user_interaction(session.turn[-1].user_request.interaction,
                                        intents_list=['NoIntent']):
                session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                output.speech_text += "Ok, never mind! "
            else:
                # Default case
                statements: List[Statement] = self.__get_conditions(session)
                condition_id: str = session.task.state.condition_id_eval
                eval_statement = [statement for statement in statements if statement.node_id == condition_id][0]

                if eval_statement.default.lower() == 'yes':
                    session.task.state.true_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a Yes, since it is the better option!"
                elif eval_statement.default.lower() == 'no':
                    session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a No, since it is the better option!"
                else:
                    logger.warning(f"WARNING: Default condition value does not match the yes/no "
                                   f"expected value. It got instead {eval_statement.default}.")

                    # For not matching Yes/No values we consider the default action to be No
                    session.task.state.false_statements_ids.append(session.task.state.condition_id_eval)
                    output.speech_text += "Uhm, I'm not sure I understand! I'll just take it as " \
                                          "a No, since it is the better option!"

            session.task.state.condition_id_eval = ""
            output = repeat_screen_response(session, output)

            if not session.headless:
                output.idle_timeout = 1800
                output.pause_interaction = True

            return session, output
        else:
            return None, None

    def get_condition(self, session: Session) -> Optional[str]:
        """
        Returns a Condition Request if it is available from the graph.
        If more than 1 condition is present we just take the first one.
        """
        statements = self.__get_conditions(session)

        if session.task.state.condition_id_eval == "" and len(statements) > 0:
            # We have conditions that need to be resolved but we don't have asked any yet

            target_condition: Statement = statements[0]
            session.task.state.condition_id_eval = target_condition.node_id

            return target_condition.body
        else:
            return None
