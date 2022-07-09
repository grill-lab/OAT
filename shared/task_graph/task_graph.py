from taskmap_pb2 import TaskMap, TaskState, Connection, ExtraInfo
from typing import List, Dict, Optional, Tuple, Set
import uuid
from .nodes import *
from .abstract_task_graph_interface import TaskGraphInterface


class TaskGraph (TaskGraphInterface):
    """
    Data Structure that contains the unordered set of Nodes. The connections are defined inside the Nodes
    This data structure acts as abstraction of the current TaskMap Protobuf definition
    """

    def __init__(self, taskmap: TaskMap = None):
        self.node_set: Dict[str, AbstractNode] = dict()

        self.attribute_list = [
            'taskmap_id',
            'title',
            'date',
            'source_url',
            'description',
            'voice_summary',
            'thumbnail_url',
            'active_time_minutes',
            'total_time_minutes',
            'rating_out_100',
            'serves',
            'headless',
            'dataset',
            'author',
            'rating_count',
            'domain_name',
            'difficulty',
            'views'
        ]

        self.tags: List[str] = []
        # self.extra: List[Dict[str, str]] = []
        self.faq: List[Dict[str, str]] = []

        if taskmap is not None:
            # Parsing Metadata
            for attr_name in self.attribute_list:
                attr_value = getattr(taskmap, attr_name)
                setattr(self, attr_name, attr_value)

            self.tags: List[str] = list(taskmap.tags)

            # for proto_extra in taskmap.extra_information:
            #     self.extra.append({
            #         'type': TaskMap.ExtraInfo.InfoType.Name(proto_extra.type),
            #         'text': proto_extra.text
            #     })

            for proto_faq in taskmap.faq:
                self.faq.append({
                    'question': proto_faq.question,
                    'answer': proto_faq.answer
                })

            # Building Graph
            node_list = taskmap.requirement_list[:] + \
                        taskmap.recommendation_list[:] + \
                        taskmap.condition_list[:] + \
                        taskmap.steps[:] + \
                        taskmap.logic_nodes_list[:] + \
                        taskmap.actions_list[:] + \
                        taskmap.extra_information[:]

            proto_node: ProtoNode
            for proto_node in node_list:
                self.__create_node(proto_node)

            connection: Connection
            for connection in taskmap.connection_list:
                self.add_connection(node_id_from=connection.id_from,
                                    node_id_to=connection.id_to,
                                    )

    def get_node(self, node_id: str) -> AbstractNode:
        return self.node_set.get(node_id, None)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self.node_set.keys()

    def __len__(self):
        return len(self.node_set)

    def add_node(self, node: AbstractNode) -> str:
        """
        Assumption: The node ID is not been initialized, or the current value can be ignored

        This function is to be used to Build a new TaskMap or augment an existing one
        """
        # ID generation
        node.node_id = str(uuid.uuid4())
        self.__add_node(node_id=node.node_id,
                        node=node)

        return node.node_id

    def __add_node(self, node_id: str, node: AbstractNode) -> None:

        assert node_id not in self, "Trying to insert duplicated Node ID, \
                                      each Node should have a unique ID"
        assert node_id == node.node_id, "Trying to insert a node with a non matching internal ID,\
                                        expecting %s but found %s" % (node.node_id, node_id)

        self.node_set[node_id] = node

    def __create_node(self, proto_node: ProtoNode) -> None:
        """DONE"""

        new_node = builder(proto_node)
        self.__add_node(new_node.node_id, new_node)

    def remove_node(self, node: AbstractNode) -> None:

        # For each child we remove parent connections
        child: AbstractNode
        for child in node.get_children():
            child.parent_list.remove(node)

        # For each parent we remove the children connections
        parent: AbstractNode
        for parent in node.parent_list:
            parent.child_list.remove(node)

        # Remove element from the node_set
        del self.node_set[node.node_id]

    def add_connection(self, node_id_from: str, node_id_to: str) -> None:

        assert node_id_to in self and node_id_from in self, \
            "Broken connection from Node %s to %s" % (node_id_from, node_id_to)

        parent_node: AbstractNode = self.get_node(node_id_from)
        child_node: AbstractNode = self.get_node(node_id_to)

        child_node.append_parent(parent_node)
        parent_node.append_child(child_node)

    def get_root_node(self) -> Optional[AbstractNode]:

        # Takes a random node in the set and returns it if it has no parent connections
        for node in self.node_set.values():
            if len(node.parent_list) == 0 and \
                    node.is_schedulable():
                return node
        # In this situation we either cannot execute the remaining nodes,
        # or some conditions still need to be satisfied
        return None

    def add_extra_info(self, info_type: str, text: str) -> None:

        try:
            # Checks if the info_type is one of the Enum InfoTypes
            ExtraInfo.InfoType.Value(info_type)
        except ValueError as e:
            raise Exception("InfoType %s string not recognized" % info_type)

        """
        Updating to treat the ExtraInfo as a Node in the Graph. 
        Connections are expected to be added outside.
        """
        node = ExtraNode(extra_type=info_type,
                         text=text)
        self.add_node(node)

    def add_faq(self, question: str, answer: str) -> None:
        self.faq.append({
            "question": question,
            "answer": answer,
        })

    def set_attribute(self, attr_name: str, attr_value: str) -> None:
        # Safety check
        assert attr_name in self.attribute_list, \
            "Unrecognized Attribute Name %s" % attr_name
        setattr(self, attr_name, attr_value)

    def update_graph(self, task_state: TaskState) -> None:
        executed_list: List[str] = []
        executed_nodes: List[AbstractNode] = []
        to_remove = []

        if task_state.index_to_next != 0:
            executed_list = task_state.execution_list[:task_state.index_to_next]
            executed_nodes = [self.get_node(node_id) for node_id in executed_list]

        resolved_ids = {}
        for node_id in task_state.true_statements_ids:
            resolved_ids[node_id] = True
        for node_id in task_state.false_statements_ids:
            resolved_ids[node_id] = False
        for node_id in executed_list:
            resolved_ids[node_id] = True

        for node in self.node_set.values():
            node.update_resolution(resolved_id_list=resolved_ids)

        for node in self.node_set.values():
            if node.resolution_status() == StatementResolution.TRUE and \
                    not isinstance(node, ExecutionNode):
                to_remove.append(node)

        for node in to_remove + executed_nodes:
            if node.node_id in self:
                self.remove_node(node)

    def to_proto(self) -> TaskMap:

        taskmap = TaskMap()

        for attr_name in self.attribute_list:
            if hasattr(self, attr_name):
                attr_value = getattr(self, attr_name)
                setattr(taskmap, attr_name, attr_value)

        taskmap.tags.extend(self.tags)

        # for obj in self.extra:
        #     extra_info = taskmap.extra_information.add()
        #
        #     extra_info.text = obj['text']
        #     extra_info.type = TaskMap.ExtraInfo.InfoType.Value(obj['type'])

        for obj in self.faq:
            faq = taskmap.faq.add()

            faq.question = obj['question']
            faq.answer = obj['answer']

        child_connection_list: Set[Tuple[str, str]] = set()
        parent_connection_list: Set[Tuple[str, str]] = set()

        for _, node in self.node_set.items():
            proto_node: ProtoNode = node.to_proto()
            proto_field: str = node.proto_list

            try:
                # Saving nodes in each list defined in the protobufs
                proto_list = getattr(taskmap, proto_field)
                proto_list.append(proto_node)

            except Exception as e:
                raise Exception(f"Field not mapped to the ProtoBuf ({str(e)})")

            for child in node.child_list:
                child_connection_list.add((node.node_id, child.node_id))

            for parent in node.parent_list:
                parent_connection_list.add((parent.node_id, node.node_id))

        assert child_connection_list == parent_connection_list, "Broken connection in the Graph!"

        for id_from, id_to in child_connection_list:
            conn: Connection = taskmap.connection_list.add()

            conn.id_from = id_from
            conn.id_to = id_to

        return taskmap
