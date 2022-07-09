from .abstract_parser import AbstractNodeParser
from task_graph import TaskGraph


class ExtraParser(AbstractNodeParser):

    # FAQs params
    question: str = ""
    answer: str = ""

    # ExtraInfo params
    type: str = ""
    text: str = ""

    def __init__(self, graph: TaskGraph):
        self.graph = graph

    def _return_node(self) -> None:
        if self._empty == "FAQ":
            self.graph.add_faq(question=self.question,
                               answer=self.answer)

        elif self._empty == "ExtraInfo":
            self.graph.add_extra_info(info_type=self.type,
                                      text=self.text)

        else:
            raise Exception("Extra information not recognized")

