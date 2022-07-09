
import sys
import os
import json
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.task_graph import TaskGraph
from taskmap_pb2 import OutputInteraction, ScreenInteraction, Image
from task_graph.nodes.execution_node import ExecutionNode
from abc import ABC, abstractmethod
from utils import get_file_system
# from ..step_requirements_linkers import StepRequirementLinker

from typing import List, Optional


# load it all in memory
requirements_lookup_dict = {}
reqs_lookup_file_path = os.path.join(
    get_file_system(), 'taskmap_generation/step_requirement_links.json'
)

with open(reqs_lookup_file_path, 'r') as reqs_lookup_file:
    for line in reqs_lookup_file:
        task_content = json.loads(line)
        requirements_lookup_dict.update(task_content)

print("lookup dict loaded")


class AbstractExecutionStep(ABC):

    def process_graph(self, task_graph, steps):
        """ Update task_graph given steps, i.e. list of (text, image url) tuples representing each execution graph. """
        prev_node_id: Optional[str] = None
        
        requirement_node_list = []
        for _, node in task_graph.node_set.items():
            if node.__class__.__name__ == "RequirementNode":
                requirement_node_list.append(node)

        if requirements_lookup_dict.get(task_graph.taskmap_id):

            # retrieve requirements/step for task
            assert task_graph.title == requirements_lookup_dict[task_graph.taskmap_id]['title']
            assert task_graph.source_url == requirements_lookup_dict[task_graph.taskmap_id]['url']

            linked_requirements: List[List[str]] = requirements_lookup_dict[task_graph.taskmap_id]['requirements_per_step']
            linked_requirement_ids: List[List[str]] = []

            # map requirement text to ids of requirement nodes
            for requirement_list in linked_requirements:
                requirement_list_ids = [
                    requirement_node.node_id for requirement_node in requirement_node_list if requirement_node.name in requirement_list
                ]

                linked_requirement_ids.append(requirement_list_ids)

        else:

            linked_requirement_ids = [[] for i in range(len(requirement_node_list))]

        for step, requirement_node_list in zip(steps, linked_requirement_ids):

            # Unpack step
            text, description, image = step

            response = OutputInteraction()
            response.speech_text = text
            response.description = description

            # Screen Interaction
            response.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
            response.screen.headline = "Step %d out of %d"
            response.screen.paragraphs.append(text)

            # Add image if present.
            if len(image) > 0:
                screen_image: Image = response.screen.image_list.add()
                screen_image.path = image

            node = ExecutionNode(
                response=response
            )
            current_node_id: str = task_graph.add_node(node)

            # add requirements
            for requirement_node_id in requirement_node_list:
                task_graph.add_connection(requirement_node_id, current_node_id)
            
            if prev_node_id is not None:
                task_graph.add_connection(prev_node_id, current_node_id)

            prev_node_id = current_node_id

        return task_graph

    @abstractmethod
    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Method for processing steps. """
        pass
