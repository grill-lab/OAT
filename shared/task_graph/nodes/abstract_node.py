from abc import ABC, abstractmethod
from enum import Enum
from taskmap_pb2 import ExecutionStep, Recommendation, Requirement, Condition, LogicNode
from typing import List, Union, Mapping, Any
import uuid


class StatementResolution(Enum):
    UNRESOLVED = 1
    TRUE = 2
    FALSE = 3


ProtoNode = Union[ExecutionStep, Recommendation, Requirement, Condition, LogicNode]


# Hack to be able to define recursive typing in the Node class
class AbstractNode: pass
class AbstractNode(ABC):

    def __init__(self,
                 node_id: str = "",
                 ):
        self.node_id: str = node_id

        if self.node_id == "":
            self.node_id = str(uuid.uuid4())

        self.status = StatementResolution.UNRESOLVED

        self.child_list: List[AbstractNode] = []
        self.parent_list: List[AbstractNode] = []

    def resolution_status(self) -> StatementResolution:
        return self.status

    def append_child(self, node: AbstractNode) -> None:
        assert node not in self.parent_list, "Error, Parent Node cannot be Child"

        self.child_list.append(node)

    def get_children(self) -> List[AbstractNode]:
        # Returns a filtered list with just the satisfied conditions
        return [child for child in self.child_list]

    def append_parent(self, node: AbstractNode) -> None:
        assert node is not self, "Error, circular dependency to self"
        assert node not in self.child_list, "Error, Child Node cannot be Parent"

        self.parent_list.append(node)

    def update_resolution(self, resolved_id_list: Mapping[str, bool]) -> None:

        if self.node_id in resolved_id_list.keys():
            if resolved_id_list.get(self.node_id):
                self.status = StatementResolution.TRUE
            else:
                self.status = StatementResolution.FALSE

    @property
    @abstractmethod
    def proto_list(self) -> str:
        """
        Property that defines in which list the node will be saved inside the protobuf object
        """
        pass

    @abstractmethod
    def to_proto(self) -> ProtoNode:
        pass

    @abstractmethod
    def is_schedulable(self) -> bool:
        pass

    @staticmethod
    def parse_proto(proto: Any) -> AbstractNode:
        raise NotImplementedError("Protobuf Parsing not implemented for abstract class")
