from abc import ABC, abstractmethod
from .nodes import AbstractNode
from taskmap_pb2 import TaskMap, TaskState
from typing import Optional


# Abstract class to define a fixed interface and to hold documentation for each function
class TaskGraphInterface(ABC):

    """
    FOR TASKMAP CREATION AND AUGMENTATION
    """

    @abstractmethod
    def __init__(self, taskmap: TaskMap = None):
        pass

    @abstractmethod
    def add_node(self, node: AbstractNode) -> str:
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> AbstractNode:
        pass

    @abstractmethod
    def add_connection(self, id_from: str, it_to: str) -> None:
        pass

    @abstractmethod
    def set_attribute(self, attr_name: str, attr_value: str) -> None:
        pass

    @abstractmethod
    def add_extra_info(self, info_type: str, text: str) -> None:
        pass

    @abstractmethod
    def add_faq(self, question: str, answer: str) -> None:
        pass

    @abstractmethod
    def to_proto(self) -> TaskMap:
        pass

    """
    FOR SCHEDULING AND GRAPH MANIPULATION
    """

    @abstractmethod
    def remove_node(self, node: AbstractNode) -> None:
        pass

    @abstractmethod
    def update_graph(self, task_state: TaskState) -> None:
        pass

    @abstractmethod
    def get_root_node(self) -> Optional[AbstractNode]:
        pass
