from utils import logger
from task_graph import ExecutionNode, ConditionNode, NotNode, AnyNode
from taskmap_pb2 import OutputInteraction, ScreenInteraction
from .abstract_parser import process_execution_steps, check_for_multiple_sections


def build_introducing_node(method_steps, task_graph, method=True):
    """ Method to build an execution node that introduces the non-linearity of the task.
        Args:
            - method_steps: a list of dictionaries containing a list of CustomDocument.Steps and a method name
                [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]
            - task_graph: the task graph representing the task
            - method: a boolean which is set True if we have a method, False if we have parts
        Returns:
            the execution node ID of the introduction node
    """
    # build starting node - introducing that we have multiple parts/ methods to this task
    output_interaction = OutputInteraction()

    # if method == True then we have methods, else we have parts
    output_interaction.screen.paragraphs.append(f"{task_graph.title} has multiple {'methods' if method else 'parts'}. "
                                                f"The first is: {method_steps[0]['method_name']}. "
                                                f"The second is: {method_steps[1]['method_name']}. "
                                                f"Do you want to do \"{method_steps[0]['method_name']}\"?")
    output_interaction.speech_text = f"{task_graph.title} has multiple {'methods' if method else 'parts'}. " \
                                     f"The first is: {method_steps[0]['method_name']}. " \
                                     f"The second is: {method_steps[1]['method_name']}. "
    output_interaction.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

    start_node = ExecutionNode(
        response=output_interaction
    )
    intro_node_id: str = task_graph.add_node(start_node)

    return intro_node_id


def create_parts(method_steps, task_graph):
    """ Creates a non-linear flow of execution. Can be scaled up linearly for any number of parts available.
        This uses ExecutionNodes, ConditionNodes, NotNodes and AnyNodes.
    Args:
        - method_steps: a list of dictionaries containing a list of CustomDocument.Steps and a method name
            [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]
        - task_graph: the task graph representing the task
    """

    logger.info(f'Creating parts for {task_graph.title}')

    method = False
    intro_node_id = build_introducing_node(method_steps, task_graph, method=method)
    current_node_id = intro_node_id

    start_sentence_string = "First,"

    for part in method_steps:
        # creating condition node for executing the part or not
        condition_text = f"{start_sentence_string} do you want to do \" {part['method_name']}\"?"
        condition_node = ConditionNode(condition_text=condition_text, default="yes")
        condition_node_id = task_graph.add_node(condition_node)
        task_graph.add_connection(current_node_id, condition_node_id)

        # creating execution nodes for each stream
        start_stream_node_id, end_stream_node_id = process_execution_steps(steps=part["steps"],
                                                                           task_graph=task_graph)
        task_graph.add_connection(condition_node_id, start_stream_node_id)

        not_node = NotNode()
        not_node_id = task_graph.add_node(not_node)
        task_graph.add_connection(condition_node_id, not_node_id)

        # joining the streams back together (part executed and part skipped)
        any_node = AnyNode()
        any_node_id = task_graph.add_node(any_node)
        task_graph.add_connection(end_stream_node_id, any_node_id)
        task_graph.add_connection(not_node_id, any_node_id)

        current_node_id = any_node_id

        start_sentence_string = "Next,"

    # now all parts have been added
    output_interaction = OutputInteraction()
    output_interaction.screen.paragraphs.append("Well done, you completed the method")
    output_interaction.speech_text = "Well done, you completed the method"
    output_interaction.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

    end_node = ExecutionNode(
        response=output_interaction
    )
    end_node_id = task_graph.add_node(end_node)
    task_graph.add_connection(current_node_id, end_node_id)


def create_methods(method_steps, task_graph):
    """ Creates a non-linear flow of execution. Can currently just be used for two methods.
        This uses ExecutionNodes, ConditionNodes, NotNodes and AnyNodes.
    Args:
        - method_steps: a list of dictionaries containing a list of CustomDocument.Steps and a method name
            [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]
        - task_graph: the task graph representing the task
    """

    logger.info(f'Creating methods for {task_graph.title}')

    # build starting node - introducing that we have multiple methods
    intro_node_id = build_introducing_node(method_steps, task_graph, method=True)

    # creating condition node to ask for which method to do
    condition_text = f"Do you want to do the first method \" {method_steps[0]['method_name']}\"?"
    condition_node = ConditionNode(condition_text=condition_text, default="yes")
    condition_node_id = task_graph.add_node(condition_node)
    task_graph.add_connection(intro_node_id, condition_node_id)

    # creating execution nodes for Stream 1
    start_stream1_node_id, end_stream1_node_id = process_execution_steps(steps=method_steps[0]["steps"],
                                                                         task_graph=task_graph)
    task_graph.add_connection(condition_node_id, start_stream1_node_id)

    # creating execution nodes for Stream 2
    not_node = NotNode()
    not_node_id = task_graph.add_node(not_node)
    start_stream2_node_id, end_stream2_node_id = process_execution_steps(steps=method_steps[1]["steps"],
                                                                         task_graph=task_graph)
    task_graph.add_connection(condition_node_id, not_node_id)
    task_graph.add_connection(not_node_id, start_stream2_node_id)

    # joining the streams back together
    any_node = AnyNode()
    any_node_id = task_graph.add_node(any_node)
    task_graph.add_connection(end_stream1_node_id, any_node_id)
    task_graph.add_connection(end_stream2_node_id, any_node_id)

    # adding a well done ending node
    output_interaction = OutputInteraction()
    output_interaction.screen.paragraphs.append("Well done, you completed the method")
    output_interaction.speech_text = "Well done, you completed the method"
    output_interaction.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

    end_node = ExecutionNode(
        response=output_interaction
    )
    end_node_id = task_graph.add_node(end_node)
    task_graph.add_connection(any_node_id, end_node_id)
