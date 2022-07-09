from .abstract_parser import AbstractNodeParser
from task_graph import ConditionNode

class ConditionParser(AbstractNodeParser):

    condition_text: str = ""
    default: str = ""

    def _return_node(self) -> ConditionNode:
        return ConditionNode(condition_text=self.condition_text,
                             default=self.default)
