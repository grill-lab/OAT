from abc import abstractmethod, ABC
from task_graph import AbstractNode


class AbstractNodeParser(ABC):

    _empty: str = "Undefined"

    def parse(self, group_list) -> AbstractNode:
        for el in group_list:
            if el['type'] == 'text':
                if "\n" not in el['originalText']:
                    label = ""
                    content = el['originalText']
                else:
                    label, content = el['originalText'].split("\n")[:2]

                self._parse_field(label, content)
        return self._return_node()

    def _parse_field(self, label, content):
        if label != "":
            setattr(self, label, content)
        else:
            self._empty = content

    @abstractmethod
    def _return_node(self) -> AbstractNode:
        pass
