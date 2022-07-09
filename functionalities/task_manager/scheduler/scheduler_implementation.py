from taskmap_pb2 import TaskMap, TaskState
from typing import List
from task_graph import TaskGraph, AbstractNode

def schedule(taskmap: TaskMap, task_state: TaskState = None) -> List[str]:

    graph: TaskGraph = TaskGraph(taskmap)
    state = TaskState()
    if state is not None:
        state.CopyFrom(task_state)

    task_state = state

    # remove from the graph the nodes that have already been executed
    graph.update_graph(task_state)

    topological_order: List[str] = []
    while graph:  # While graph is not empty
        # A root node is a node that does not have any dependencies
        root_node: AbstractNode = graph.get_root_node()

        if root_node is None:
            del task_state.execution_list[task_state.index_to_next:]
            task_state.execution_list.extend(topological_order)
            task_state.index_to_next += len(topological_order)
            graph: TaskGraph = TaskGraph(taskmap)
            graph.update_graph(task_state)
            root_node: AbstractNode = graph.get_root_node()

        if root_node is None:
            break  # No node can be scheduled at this moment

        topological_order.append(root_node.node_id)
        graph.remove_node(root_node)  # this removes all the dependencies from this node

    return topological_order
