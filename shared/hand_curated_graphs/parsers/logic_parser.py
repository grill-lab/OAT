from .abstract_parser import AbstractNodeParser
from task_graph.nodes.logic_nodes import *

class LogicParser(AbstractNodeParser):

    def _return_node(self) -> AbstractLogicNode:

        class_map = {
            "NOT": NotNode,
            "ANY": AnyNode,
            "WAIT": WaitNode
        }
        assert self._empty in class_map.keys(), f"Logic node miss-configured! {self._empty} " \
                                                f"is not a valid value for a logic node"

        return class_map[self._empty]()
