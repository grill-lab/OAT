import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.nodes.requirement_node import RequirementNode
from abc import ABC, abstractmethod
from typing import List

class AbstractStepRequirementLinker(ABC):

    @abstractmethod
    def link_requirements_to_step(
        self, step: str, requirement_node_list: List[RequirementNode]
    ) -> List[str]:
        """Method for extracting the requirements needed for a step"""