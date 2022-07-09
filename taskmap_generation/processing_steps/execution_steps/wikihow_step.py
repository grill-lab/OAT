
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

import re
from processing_steps.execution_steps.abstract_execution_step import AbstractExecutionStep
from task_graph.task_graph import TaskGraph


class StepExecutionWikihow(AbstractExecutionStep):

    def __clean_wikihowSteps(self, step):
        if len(step) <= 8:
            return ''
        if '.com' in step:
            return ''
        # Match any html tag
        pattern = re.compile("<(\"[^\"]*\"|'[^']*'|[^'\">])*>")
        if pattern.match(step):
            return ''
        # Match any url
        pattern = re.compile("https?:\/\/(?:[-\w.]|(?:%[\da-fA-F]{2}))+")
        if pattern.match(step):
            return ''
        return step

    def __merge_steps_sentence(self, sentence_1, sentence_2):
        sentence_1_split = sentence_1.split(" ")
        sentence_2_split = sentence_2.split(" ")
        if len(sentence_1_split) + len(sentence_2_split) <= 20:
            return f"{sentence_1} {sentence_2}", ""
        return sentence_1, sentence_2

    def __build_steps(self, document):
        """ Method for processing steps. """
        steps = []
        if 'steps' in document:
            if len(document['steps']) > 0:
                for step in document['steps']:
                    text = step['headline']
                    text = self.__clean_wikihowSteps(step=text)
                    if text:
                        description = step['description']
                        description = self.__clean_wikihowSteps(step=description)
                        text, description = self.__merge_steps_sentence(text, description)
                        if step['img']:
                            image = step['img']
                        else:
                            image = ''
                        steps.append((text, description, image))
                return steps

        if 'parts' in document:
            for part in document['parts']:
                for step in part['steps']:
                    text = step['headline']
                    text = self.__clean_wikihowSteps(step=text)
                    if text:
                        description = step['description']
                        description = self.__clean_wikihowSteps(step=description)
                        text, description = self.__merge_steps_sentence(text, description)
                        if step['img']:
                            image = step['img']
                        else:
                            image = ''
                        steps.append((text, description, image))

        return steps

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Add Wikihow execution to task_graph. """

        steps = self.__build_steps(document)
        # Added to allow exclusion of taskmaps with no steps.
        if len(steps) > 0:
            return self.process_graph(task_graph=task_graph, steps=steps)
        else:
            return task_graph