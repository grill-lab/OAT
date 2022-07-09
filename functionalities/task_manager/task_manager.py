from .abstract_task_manager import AbstractTaskManager
from task_manager_pb2 import TMResponse, TMRequest, InfoRequest, InfoResponse, Statement, ExtraList, TMInfo
from taskmap_pb2 import TaskState, TaskMap, OutputInteraction, Transcript, ScreenInteraction
from .scheduler import schedule
from exceptions import EndOfExecutionException
from task_graph import TaskGraph
from task_graph.nodes import *
from typing import Any, Callable, List, Optional
from utils import get_credit_from_taskmap, build_video_button
from itertools import chain, combinations


def verbal_progress(current_step, step_length):
    if current_step == 1:
        speech_text = f"Step {current_step} out of {step_length}. "
    else:
        speech_text = f"Step {current_step}. "

    if (current_step / step_length == 0.5) or (current_step / step_length + 1 == 0.5):
        speech_text += f"Halfway there! "

    return speech_text


def test_sub_graph_any(node: AbstractNode, test_fn: Callable[[AbstractNode], bool]) -> bool:
    # Function that tests all of the subgraph of a specific node
    if not node.get_children():
        return test_fn(node)
    else:
        return test_fn(node) or any([test_fn(child_node) for child_node in node.get_children()])


def manage_progress(request: TMRequest, action: str) -> TMResponse:
    state: TaskState = request.state
    taskmap: TaskMap = request.taskmap
    index_to_goto: int = request.attribute

    if (
        action == 'next' and (
            len(state.execution_list) == 0 or
            state.index_to_next >= len(state.execution_list)
        )
    ) or (
        action == 'go_to' and (
            len(state.execution_list) == 0 or
            abs(index_to_goto) > len(state.execution_list)
        )
    ):
        # In this cases we need to reschedule the missing nodes
        next_steps = schedule(taskmap=taskmap,
                              task_state=state)

        del state.execution_list[state.index_to_next:]

        if len(next_steps) == 0 or len(state.execution_list) + len(next_steps) <= abs(index_to_goto):
            raise EndOfExecutionException("The Step node requested cannot be scheduled")

        state.execution_list.extend(next_steps)

    # States uses the index_to_next variable to handle the default
    # value of 0 for the protobuf. This means that if the index_to_next is 0
    # we have never given any instruction yet. We will then return always the first
    # instruction. In all the other cases, we move the index and take the response
    # that we need depending on the instruction

    if action == 'next' or state.index_to_next == 0:
        response_id: str = state.execution_list[state.index_to_next]
        state.index_to_next += 1
    elif action == 'prev' and state.index_to_next >= 2:
        response_id: str = state.execution_list[state.index_to_next - 2]
        state.index_to_next -= 1
    elif action == 'repeat':
        response_id: str = state.execution_list[state.index_to_next - 1]
    elif action == 'go_to':
        if index_to_goto > 0:
            response_id: str = state.execution_list[index_to_goto - 1]
            state.index_to_next = index_to_goto
        else:
            response_id: str = state.execution_list[index_to_goto]
            state.index_to_next = len(state.execution_list) + index_to_goto + 1

    else:
        response_id: str = state.execution_list[state.index_to_next - 1]

    # Return the response verbatim from the taskmap.
    task_graph = TaskGraph(taskmap=taskmap)
    exec_node: Any = task_graph.get_node(response_id)
    output: OutputInteraction = exec_node.response
    exec_node.response.speech_text = f"{verbal_progress(state.index_to_next, len(state.execution_list))}" \
                                     f"{exec_node.response.speech_text}"
    output.screen.footer = f'{taskmap.title}'
    output.screen.headline = f"Step {state.index_to_next}"
    output.screen.hint_text = "next"

    if not taskmap.headless:
        speech_text, new_screen = build_video_button(output, output.screen.video)
        output.screen.ParseFromString(new_screen.SerializeToString())
        output.speech_text += speech_text
    # if more details found, add more details button
    if exec_node.response.description != "":
        output.screen.buttons.append("Details")
        output.screen.on_click_list.append("details")

    if len(output.screen.buttons) == 0 and state.index_to_next != 1:
        output.screen.buttons.append("Previous")
        output.screen.on_click_list.append("Previous")
    if len(output.screen.buttons) < 2:
        output.screen.buttons.append("Next")
        output.screen.on_click_list.append("next step")

    # Creating Response Object
    response = TMResponse()
    response.interaction.ParseFromString(output.SerializeToString())
    response.updated_state.ParseFromString(state.SerializeToString())

    return response


def extract_statements(request: InfoRequest, statement_type: str) -> InfoResponse:
    if request.resolve:
        raise NotImplementedError("Automatic Resolution of Statements is not supported yet!")

    taskmap: TaskMap = request.taskmap
    state: TaskState = request.state
    graph: TaskGraph = TaskGraph(taskmap)

    if len(state.execution_list) > state.index_to_next - 1 > -1 and request.local:
        current_node_id: str = state.execution_list[state.index_to_next - 1]
        current_node = graph.get_node(current_node_id)
    else:
        current_node = None

    def extract_nodes_by_type(
            node_list: List[AbstractNode],
            node_type: type,
            node_to_statement: Callable[[Any], Optional[Statement]]):
        assert issubclass(node_type, AbstractNode), "Invalid Node Type to extract from the Graph"

        response: InfoResponse = InfoResponse()

        for node in node_list:
            if isinstance(node, node_type):
                node: node_type
                statement = node_to_statement(node)

                if statement is not None:
                    out: Statement = response.unresolved_statements.add()
                    out.CopyFrom(statement)

        return response

    if statement_type == "requirements":

        if request.local and current_node is not None:
            node_list = current_node.parent_list
        else:
            node_list = graph.node_set.values()

        def convert(node: RequirementNode) -> Statement:
            statement: Statement = Statement()
            statement.node_id = node.node_id
            statement.body = node.name
            statement.amount = node.amount
            statement.taskmap_reference_id = node.linked_taskmap_id
            return statement

        return extract_nodes_by_type(node_list, RequirementNode, convert)

    elif statement_type == "conditions":
        # To extract the current conditions we need to update the graph based on the current state
        graph.update_graph(state)

        def convert(node: ConditionNode) -> Statement:
            if len(node.parent_list) == 0 and node.resolution_status() == StatementResolution.UNRESOLVED:
                statement: Statement = Statement()
                statement.body = node.condition_text
                statement.node_id = node.node_id
                statement.default = node.default
                return statement

        # Extract all Condition nodes without dependencies
        return extract_nodes_by_type(graph.node_set.values(), ConditionNode, convert)

    elif statement_type == "actions":
        # To extract the current conditions we need to update the graph based on the current state
        graph.update_graph(state)

        def convert(node: ActionNode) -> Statement:
            if len(node.parent_list) == 0 and node.resolution_status() == StatementResolution.UNRESOLVED:
                statement: Statement = Statement()
                statement.body = node.action_text
                statement.node_id = node.node_id
                return statement

        # Extract all Action nodes without dependencies
        return extract_nodes_by_type(graph.node_set.values(), ActionNode, convert)


class TaskManager(AbstractTaskManager):

    def get_step(self, request: TMRequest) -> OutputInteraction:
        state: TaskState = request.state
        taskmap: TaskMap = request.taskmap
        response_id: str = state.execution_list[state.index_to_next - 1]
        # Return the response verbatim from the taskmap.
        task_graph = TaskGraph(taskmap=taskmap)
        exec_node: Any = task_graph.get_node(response_id)
        return exec_node.response

    def previous(self, request: TMRequest) -> TMResponse:
        return manage_progress(request, "prev")

    def repeat(self, request: TMRequest) -> TMResponse:
        return manage_progress(request, "repeat")

    def next(self, request: TMRequest) -> TMResponse:
        return manage_progress(request, "next")

    def go_to(self, request: TMRequest) -> TMResponse:
        return manage_progress(request, "go_to")

    def more_details(self, request: TMRequest) -> OutputInteraction:
        state: TaskState = request.state
        taskmap: TaskMap = request.taskmap

        response_id: str = state.execution_list[state.index_to_next - 1]

        # Return the response verbatim from the taskmap.
        task_graph = TaskGraph(taskmap=taskmap)
        exec_node: Any = task_graph.get_node(response_id)

        if exec_node.response.description != "":
            output: OutputInteraction = OutputInteraction()
            output.speech_text = exec_node.response.description
            output.screen.image_list.extend(exec_node.response.screen.image_list)
            output.screen.paragraphs.append(exec_node.response.description)

            # if more details found, add more details button
            output.screen.buttons.append(f"Back to step {state.index_to_next}")
            output.screen.on_click_list.append(f"Back to step {state.index_to_next}")
            output.screen.hint_text = "let's continue"
        else:
            output: OutputInteraction = exec_node.response
            output.speech_text = "I don't know more details about this step. If you want to hear the step " \
                                 "again, say 'repeat' or say 'next' to keep going. "

        if not taskmap.headless:
            speech_text, screen = build_video_button(output, exec_node.response.screen.video)
            # add next step and repeat buttons

            output.screen.ParseFromString(screen.SerializeToString())
            output.speech_text += speech_text
            if len(output.screen.buttons) == 0:
                output.screen.buttons.append("Previous")
                output.screen.on_click_list.append("previous")

            output.screen.buttons.append("Next")
            output.screen.on_click_list.append("Next")
            output.screen.hint_text = "next"

        output.screen.footer = f'{taskmap.title}'
        output.screen.headline = f"Step {state.index_to_next}"
        output.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        return output

    def get_transcript(self, request: TMRequest) -> Transcript:
        response: Transcript = Transcript()

        response.title = request.taskmap.title
        response.image_url = request.taskmap.thumbnail_url

        response.body = f"I'm happy to help you with {request.taskmap.title}.\n"

        credit: str = get_credit_from_taskmap(request.taskmap)
        rating: float = request.taskmap.rating_out_100/20
        response.body += f"This task is coming from {credit}, and it has an average rating of {rating:.1f} / 5." \
                         f" The instructions are below: \n\n"

        # stupid fix, fix properly later
        for idx, step in enumerate(request.taskmap.steps[:20]):
            response.body += f"{idx}. {step.response.speech_text.split('.')[0]}\n"

        return response

    @staticmethod
    def get_requirements(request: InfoRequest) -> InfoResponse:
        return extract_statements(request, "requirements")

    @staticmethod
    def get_conditions(request: InfoRequest) -> InfoResponse:
        return extract_statements(request, "conditions")

    @staticmethod
    def get_actions(request: InfoRequest) -> InfoResponse:
        return extract_statements(request, "actions")

    @staticmethod
    def get_extra(request: InfoRequest) -> ExtraList:

        taskmap: TaskMap = request.taskmap
        state: TaskState = request.state
        graph: TaskGraph = TaskGraph(taskmap)
        graph.update_graph(state)

        # Fetching current Node
        current_node = None
        if len(state.execution_list) > state.index_to_next - 1 > -1:
            current_node_id: str = state.execution_list[state.index_to_next - 1]
            current_node = graph.get_node(current_node_id)

        local_extra = []
        global_extra = []
        response = ExtraList()

        for node in graph.node_set.values():
            if isinstance(node, ExtraNode) and node.resolution_status() == StatementResolution.UNRESOLVED:

                if current_node is not None and node in current_node.child_list:
                    # We have current Node and the Extra is its child
                    local_extra.append(node.to_proto())
                elif len(node.parent_list) == 0:
                    # Node has no Parents
                    global_extra.append(node.to_proto())

        response.extra_list.extend(local_extra or global_extra)
        return response

    @staticmethod
    def get_num_steps(request: TMRequest) -> TMInfo:

        taskmap: TaskMap = request.taskmap
        state: TaskState = request.state
        graph: TaskGraph = TaskGraph(taskmap)
        graph.update_graph(state)  # This should remove all the already resolved conditions

        condition_nodes = set()
        for node in graph.node_set.values():
            if isinstance(node, ConditionNode) and \
                    node.resolution_status() == StatementResolution.UNRESOLVED and \
                    test_sub_graph_any(node, lambda child_node: isinstance(child_node, ExecutionNode)):
                # Get all Condition nodes that can lead to a set of Execution Nodes
                condition_nodes.add(node)

        exec_lengths = []
        if len(condition_nodes) == 0:
            exec_list = schedule(taskmap, state)
            exec_lengths.append(len(exec_list))
        else:
            # Test all possible combinations of conditions to test the length of each graph
            for node_subset in chain.from_iterable([combinations(condition_nodes, k)
                                                    for k in range(len(condition_nodes)+1)
                                                    ]):
                tmp_state = TaskState()
                tmp_state.CopyFrom(state)

                tmp_state.true_statements_ids.extend([node.node_id for node in node_subset])
                tmp_state.false_statements_ids.extend([node.node_id for node in condition_nodes - set(node_subset)])

                exec_list = schedule(taskmap, tmp_state)
                exec_lengths.append(len(exec_list))

        response = TMInfo()
        response.min_number_steps = min(exec_lengths)
        response.max_number_steps = max(exec_lengths)
        response.current_step = state.index_to_next - 1

        return response
