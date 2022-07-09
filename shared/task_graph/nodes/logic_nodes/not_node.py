from .abstract_logic_node import AbstractLogicNode
from .. import AbstractNode, StatementResolution, ConditionNode
from typing import Any


class NotNode(AbstractLogicNode):

    @staticmethod
    def parse_proto(proto: Any) -> AbstractNode:
        return NotNode(node_id=proto.unique_id)

    def _pre_condition(self, node: AbstractNode) -> bool:
        """
        Condition before appending a parent. For the NotNode we accept only one parent
        Parent Node can only be a ConditionNode or another AbstractLogicNode
        """
        return len(self.parent_list) == 0 and (
            isinstance(node, ConditionNode) or
            isinstance(node, AbstractLogicNode)
        )

    def resolution_status(self) -> StatementResolution:
        if len(self.parent_list) == 0:
            # When a Node is True is removed, we assumed that a connection existed and
            # the Not Node is then considered True
            return StatementResolution.TRUE

        parent = self.parent_list[0]

        if parent.resolution_status() == StatementResolution.UNRESOLVED:
            return StatementResolution.UNRESOLVED

        if parent.resolution_status() == StatementResolution.FALSE:
            return StatementResolution.TRUE
        else:
            return StatementResolution.FALSE
