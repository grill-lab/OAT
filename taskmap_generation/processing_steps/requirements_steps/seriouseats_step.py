
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.task_graph import TaskGraph
from task_graph.nodes.requirement_node import RequirementNode
from processing_steps.requirements_steps.abstract_requirements_step import AbstractRequirementsStep


class StepSeriouseatsRequirements(AbstractRequirementsStep):

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Add Recipe 1M+ requirements to task_graph. """

        for r in document['material_total']:
            node = RequirementNode(
                name=str(r),
                req_type='HARDWARE',
                amount='',
                linked_taskmap_id=''
            )
            task_graph.add_node(node)

        return task_graph
