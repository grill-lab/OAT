
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.task_graph import TaskGraph
from processing_steps.execution_steps.abstract_execution_step import AbstractExecutionStep


class StepSeriouseatsExecution(AbstractExecutionStep):

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """  Method for processing steps. """
        steps = []
        for step_text, step_images in zip(document['steps'], document['steps_images']):
            text = str(step_text)
            description = ''
            if step_images:
                image = str(step_images[0])
            else:
                image = ''

            steps.append((text, description, image))

        return self.process_graph(task_graph=task_graph, steps=steps)
