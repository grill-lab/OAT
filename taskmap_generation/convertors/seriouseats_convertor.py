
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph import *
from convertors.abstract_convertor import AbstractConvertor

from processing_steps.attributes_steps.seriouseats_step import StepSeriouseatsAttributes
from processing_steps.requirements_steps.seriouseats_step import StepSeriouseatsRequirements
from processing_steps.execution_steps.seriouseats_step import StepSeriouseatsExecution


class SeriouseatsConvertor(AbstractConvertor):

    def filter(self, task_graph):
        """ return True is valid else False if not"""
        try:
            taskmap = task_graph.to_proto()
        except:
            return False

        if not taskmap.title:
            return False

        if not taskmap.steps:
            return False

        if len(taskmap.thumbnail_url) == 0:
            return False

        num_requirements = 0 if not taskmap.requirement_list else len(taskmap.requirement_list)
        if num_requirements > 20:
            return False

        num_steps = 0 if not taskmap.steps else len(taskmap.steps)
        if num_steps > 20:
            return False

        max_step_words = max([len(step.response.speech_text.split()) for step in taskmap.steps])
        if max_step_words > 100:
            return False

        min_step_words = min([len(step.response.speech_text.split()) for step in taskmap.steps])
        if min_step_words == 0:
            return False

        return taskmap

    def document_to_task_graph(self, document) -> TaskGraph:
        """ Convert document to TaskGraph. """
        task_graph = TaskGraph()
        task_graph = StepSeriouseatsAttributes().update_task_graph(document=document, task_graph=task_graph)
        task_graph = StepSeriouseatsRequirements().update_task_graph(document=document, task_graph=task_graph)
        task_graph = StepSeriouseatsExecution().update_task_graph(document=document, task_graph=task_graph)
        return task_graph
