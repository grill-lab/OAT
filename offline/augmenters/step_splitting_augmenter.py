import nltk
import uuid

from taskmap_pb2 import ExecutionStep, Connection, OutputInteraction, TaskMap
from .abstract_augmenter import AbstractSimpleTaskGraphAugmenter
from typing import List


def get_step_text(step) -> str:
    step_text = step.response.screen.paragraphs[0]
    return step_text


def locate_connections(taskmap, step_id) -> (str, str):
    previous_connection = Connection()
    next_connection = Connection()
    correct_connections = []
    for connection in list(taskmap.connection_list):
        if connection.id_to == step_id:
            previous_connection = connection
            taskmap.connection_list.remove(connection)
        elif connection.id_from == step_id:
            next_connection = connection
            taskmap.connection_list.remove(connection)
        else:
            correct_connections.append(connection)
    return previous_connection, next_connection


class StepSplittingAugmenter(AbstractSimpleTaskGraphAugmenter):

    def __init__(self) -> None:
        super().__init__()
        nltk.download('punkt')

        with open("./augmenters/cooking_verbs.txt") as f:
            cooking_verbs = f.read()
            self.cooking_verbs = cooking_verbs.split("\n")[:-1]

    def condition(self, taskmap: TaskMap) -> bool:
        return True

    def map_split_step_by_cooking_verbs(self, step_text):
        sentences = nltk.sent_tokenize(step_text)
        sentences = [s for s in sentences if any([v in s.lower() for v in self.cooking_verbs])]
        return sentences

    @staticmethod
    def map_merge_short_neighbouring_steps(split_sentences: List[str]) -> List[str]:
        """
        Given the split sentences, for each pair of neighbouring steps, if the TOTAL
        number of words using nltk tokenize is less than 30, merge them together into one step.
        """
        merged_sentences = []
        i = 0
        while i < len(split_sentences):
            if i == len(split_sentences) - 1:
                merged_sentences.append(split_sentences[i])
                break
            else:
                if len(nltk.word_tokenize(split_sentences[i] + split_sentences[i + 1])) < 50:
                    merged_sentences.append(split_sentences[i] + " " + split_sentences[i + 1])
                    i += 2
                else:
                    merged_sentences.append(split_sentences[i])
                    i += 1
        return merged_sentences

    def get_transformed_input(self, taskmap: TaskMap):
        return taskmap

    def process_step_into_substeps(self, step: OutputInteraction) -> List[ExecutionStep]:
        """
        This function takes an execution step and returns a list of
        execution steps with shortened steps
        """
        split_steps = []

        step_text = get_step_text(step)
        split_text = self.map_split_step_by_cooking_verbs(step_text)
        merged_text = self.map_merge_short_neighbouring_steps(split_text)
        if len(merged_text) > 1:
            # Create new output interactions for each text in the text_list
            for sub_step_text in merged_text:
                sub_step = ExecutionStep()
                sub_step.unique_id = str(uuid.uuid4())
                sub_step.response.screen.MergeFrom(step.response.screen)
                del sub_step.response.screen.paragraphs[:]
                sub_step.response.screen.paragraphs.append(sub_step_text)
                sub_step.response.speech_text = sub_step_text
                split_steps.append(sub_step)

        return split_steps

    def apply_output(self, taskmap: TaskMap, processed_output) -> TaskMap:
        split_steps, correct_steps = processed_output

        if len(split_steps) > 0:

            del taskmap.steps[:]

            for split_step_id in split_steps.keys():
                previous_connection, next_connection = locate_connections(taskmap, split_step_id)

                first_connection: Connection = Connection()
                first_connection.id_from = previous_connection.id_from
                first_connection.id_to = split_steps[split_step_id][0].unique_id
                
                if first_connection.id_from != "" and first_connection.id_to != "":
                    taskmap.connection_list.append(first_connection)

                last_connection: Connection = Connection()
                last_connection.id_to = next_connection.id_to
                last_connection.id_from = split_steps[split_step_id][-1].unique_id
                
                if last_connection.id_from != "" and last_connection.id_to != "":
                    taskmap.connection_list.append(last_connection)

                for i in range(len(split_steps[split_step_id]) - 1):
                    between_connection: Connection = Connection()
                    between_connection.id_from = split_steps[split_step_id][i].unique_id
                    between_connection.id_to = split_steps[split_step_id][i+1].unique_id
                    taskmap.connection_list.append(between_connection)

                for step in split_steps[split_step_id]:
                    taskmap.steps.append(step)

            for original_step in correct_steps:
                taskmap.steps.append(original_step)

        return taskmap

    def process(self, taskmap: TaskMap) -> TaskMap:
        """"""
        correct_steps = []
        split_steps = {}

        for step in taskmap.steps:
            # Get new shortened steps
            list_of_sub_steps = self.process_step_into_substeps(step)
            if len(list_of_sub_steps) > 0:
                split_steps[step.unique_id] = list_of_sub_steps
            else:
                correct_steps.append(step)

        return split_steps, correct_steps
