from .abstract_parser import AbstractNodeParser
from task_graph import ActionNode

class ActionParser(AbstractNodeParser):

    action_code: str = ""

    def _return_node(self) -> ActionNode:
        return ActionNode(action_text=self.action_code)
