from ..abstract_node import AbstractNode, StatementResolution, ProtoNode
from abc import ABC, abstractmethod
from typing import Any
from taskmap_pb2 import LogicNode


class ViolatedConditionException(Exception):
    pass


class AbstractLogicNode(AbstractNode, ABC):

    def __init__(self,
                 **kwargs):
        super().__init__(**kwargs)

    @property
    def proto_list(self) -> str:
        return "logic_nodes_list"

    def append_parent(self, node: AbstractNode) -> None:

        if not self._pre_condition(node):
            raise ViolatedConditionException()
        super().append_parent(node)

    def to_proto(self) -> ProtoNode:
        proto = LogicNode()
        proto.unique_id = self.node_id
        proto.type = type(self).__name__

        return proto

    def is_schedulable(self) -> bool:
        return False

    @abstractmethod
    def _pre_condition(self, node: AbstractNode) -> bool:
        # Protected method that allows to enforce conditions for the logic nodes
        # An example could be the NOT Node that can only have 1 parent, or AND that might be only for 2 node (TBD)
        pass

    @abstractmethod
    def resolution_status(self) -> StatementResolution:
        pass

