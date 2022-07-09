
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from abc import ABC, abstractmethod

from task_graph import *


class AbstractConvertor(ABC):

    @abstractmethod
    def document_to_task_graph(self, document) -> TaskGraph:
        """ Convert document to TaskGraph. """
        pass
