from .abstract_logic_node import AbstractLogicNode
from .. import AbstractNode, StatementResolution
from typing import Any


class AnyNode(AbstractLogicNode):

    @staticmethod
    def parse_proto(proto: Any) -> AbstractNode:
        return AnyNode(node_id=proto.unique_id)

    def _pre_condition(self, node: AbstractNode) -> bool:
        """
        The AnyNode accept any incoming connection, so there is not Pre Condition for a connection
        """
        return True

    def resolution_status(self) -> StatementResolution:

        parents_res = [parent.resolution_status() for parent in self.parent_list]

        # If any parent is still unresolved, we consider it unresolved
        if any([res == StatementResolution.UNRESOLVED for res in parents_res]):
            return StatementResolution.UNRESOLVED
        elif any([res == StatementResolution.TRUE for res in parents_res]):
            return StatementResolution.TRUE

        return StatementResolution.FALSE
