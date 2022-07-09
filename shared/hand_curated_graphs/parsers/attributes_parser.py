from .abstract_parser import AbstractNodeParser
from task_graph import TaskGraph
from utils import get_credit_from_url
import uuid

class AttributesParser(AbstractNodeParser):

    source_url: str = ""

    def __init__(self, graph: TaskGraph):
        self.graph = graph

    def _return_node(self) -> None:

        website_name = get_credit_from_url(self.source_url)
        self.graph.set_attribute("taskmap_id", str(uuid.uuid4()))
        self.graph.set_attribute("domain_name", website_name)
        self.graph.set_attribute("dataset", "hand curated")

        for attr_name, value in self.__dict__.items():
            # Skip internal attributes
            if attr_name not in ["graph", "_empty"]:
                if "rating" in attr_name:
                    self.graph.set_attribute(attr_name, int(value))
                else:
                    self.graph.set_attribute(attr_name, value)
