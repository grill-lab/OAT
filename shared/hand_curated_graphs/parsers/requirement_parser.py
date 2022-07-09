from .abstract_parser import AbstractNodeParser
from task_graph import RequirementNode

class RequirementParser(AbstractNodeParser):

    display_text: str = ""
    requirement_type: str = ""
    amount: str = ""

    def _return_node(self) -> RequirementNode:
        return RequirementNode(name=self.display_text,
                               req_type=self.requirement_type,
                               amount=self.amount)
