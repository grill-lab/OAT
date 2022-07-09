from .abstract_logic_node import AbstractLogicNode
from .. import AbstractNode, StatementResolution, ConditionNode
from typing import Any


class WaitNode(AbstractLogicNode):

    @staticmethod
    def parse_proto(proto: Any) -> AbstractNode:
        return WaitNode(node_id=proto.unique_id)

    def _pre_condition(self, node: AbstractNode) -> bool:
        """
        Condition before appending a parent. For the WaitNode we accept only one parent
        """
        return len(self.parent_list) == 0

    def resolution_status(self) -> StatementResolution:
        if len(self.parent_list) == 0:
            # When a Node is True is removed, we assumed that a connection existed and
            # the Not Node is then considered True
            return StatementResolution.TRUE

        parent = self.parent_list[0]

        if parent.resolution_status() == StatementResolution.UNRESOLVED:
            return StatementResolution.UNRESOLVED
        else:
            return StatementResolution.TRUE
