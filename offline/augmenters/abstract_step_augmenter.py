from abc import ABC, abstractmethod
from taskmap_pb2 import OutputInteraction, TaskMap, ExecutionStep
from typing import List
from task_graph import TaskGraph
from utils import logger


class AbstractStepAugmenter(ABC):

    def __init__(self):
        self.process_dict = {}
        self.output_dict = {}

    @abstractmethod
    def get_transformed_input(self, task_graph: TaskGraph):
        pass

    @abstractmethod
    def condition(self, step: ExecutionStep) -> bool:
        """Function to evaluate whether we should augment the ExecutionStep or not
        Args: ExecutionStep
        Returns:
            - bool: True if should be augmented, False if not
        """
        pass

    def gather_inputs(self, task_maps):
        """ Step 1 """
        for task_map in task_maps:
            for step in task_map.steps:
                if self.condition(step):
                    hashval = task_map.taskmap_id + step.unique_id  # example: tg_1_sp_4
                    pre_transformed_input = self.get_transformed_input(task_map)
                    if pre_transformed_input:
                        self.process_dict[hashval] = (step, pre_transformed_input)
                    else:
                        self.process_dict[hashval] = (step, [])

    @abstractmethod
    def process_inputs_into_outputs(self):
        """ Step 2 - implemented differently for simple vs batch augmenter """
        pass

    @abstractmethod
    def apply_output(self, step: ExecutionStep, processed_output: str) -> ExecutionStep:
        pass

    def gather_outputs(self, task_graphs):
        """ Step 3 """
        for task_graph in task_graphs:
            taskmap_step_hash_vals = []
            original_steps = []
            for step in task_graph.steps:
                hash_val = task_graph.taskmap_id + step.unique_id
                taskmap_step_hash_vals.append(hash_val)
                original_steps.append(step)
            del task_graph.steps[:]

            for (i, hash_val) in enumerate(taskmap_step_hash_vals):
                processed_output = self.output_dict.get(hash_val)
                if processed_output:
                    processed_step = self.apply_output(original_steps[i], self.output_dict[hash_val])
                else:
                    processed_step = original_steps[i]
                task_graph.steps.append(processed_step)

        return task_graphs

    def augment(self, task_graphs: List[TaskMap]) -> List[TaskMap]:
        """ Augmentation function """
        self.gather_inputs(task_graphs)
        self.process_inputs_into_outputs()
        return self.gather_outputs(task_graphs)


class AbstractSimpleStepAugmenter(AbstractStepAugmenter):

    @abstractmethod
    def process(self, step: ExecutionStep, transformed_input) -> ExecutionStep:
        pass

    def process_inputs_into_outputs(self):
        """ Step 2 - Because not computational heavy can just loop over them """
        for hash_val in self.process_dict.keys():
            step, pre_transformed_input = self.process_dict[hash_val]
            processed_output = self.process(step, pre_transformed_input)
            self.output_dict[hash_val] = processed_output


class AbstractBatchStepAugmenter(AbstractStepAugmenter):

    @abstractmethod
    def batch_process(self, batch):
        """ each batch consists of a list of tuples:
            (hash_val: str, original_step: ExecutionStep, global_info: List[str] -> e.g. requirements)
        """
        pass

    def make_batches(self, batch_size=256):
        process_list = []
        for hash_val in self.process_dict.keys():
            step, pre_transformed_input = self.process_dict[hash_val]
            process_list.append((hash_val, step, pre_transformed_input))
        batches = []
        for i in range(0, len(process_list), batch_size):
            batches.append(process_list[i:i+batch_size])
        return batches

    def process_inputs_into_outputs(self):
        """ Step 2 - Doing the processing with heavy GPU """
        batches = self.make_batches()
        for batch in batches:
            outputs = self.batch_process(batch)
            for ((hash_val, _, _), output) in zip(batch, outputs):
                self.output_dict[hash_val] = output
