from taskmap_pb2 import Session, OutputInteraction, Timer
from task_manager_pb2 import Statement


def perform_action(session: Session, output: OutputInteraction, action_statement: Statement) -> None:
    """
    Method that performs the action inside an ActionNode and defines the node
    as True or False according to the return of the function
    """
    state = session.task.state

    if eval(action_statement.body):
        state.true_statements_ids.append(action_statement.node_id)
    else:
        state.false_statements_ids.append(action_statement.node_id)


"""
ACTION DOCUMENTATION:

To define a function that can be used as an action, we can define any kind of function
We can use as inputs both the {session} or the {output} interaction to modify them based on 
the action that we want to perform.

An example of an Action function could be:
    def merge_task_map(session, taskmap_id):
        ...
        
In this case, session will be taken from the current session that is been used, and we can pass 
the taskmap_id during the creation of the TaskGraph to identify which TaskMap we want to merge
with the current one

Actions HAVE TO return a bool value. This will be used to evaluate the Action Node.
We can use this to define more complex behaviors, where for example if an Action fails we can direct the user
towards a different path. This behavior can be achieved by also composing the Action Node with Logic Nodes.

"""

def set_timer(output: OutputInteraction, duration: str) -> bool:
    """
    Function that adds a createTimerIntent into the intent list of the user
    with a duration parameter and raises an exception
    """

    output.timer.timer_id = "CreateTimerID"
    output.timer.label = "User's"
    output.timer.duration = duration
    output.timer.operation = Timer.Operation.CREATE
    output.timer.time.GetCurrentTime()

    output.speech_text = "I have set the timer. " + output.speech_text
    return True
