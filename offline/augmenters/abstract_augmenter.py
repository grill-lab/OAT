from abc import ABC, abstractmethod
from taskmap_pb2 import TaskMap
from typing import List


class AbstractTaskGraphAugmenter(ABC):

    def __init__(self):
        self.process_dict = {}
        self.output_dict = {}

    @abstractmethod
    def condition(self, taskmap: TaskMap) -> bool:
        """Function to evaluate whether we should augment the task_graph or not
        Args: TaskMap
        Returns:
            - bool: True if should be augmented, False if not
        """
        pass

    @abstractmethod
    def get_transformed_input(self, taskmap: TaskMap):
        pass

    def gather_inputs(self, task_graphs):
        """ Step 1 """
        for task_graph in task_graphs:
            if self.condition(task_graph):
                hashval = task_graph.taskmap_id  # example: tg_1_sp_4
                pre_transformed_input = self.get_transformed_input(task_graph)
                self.process_dict[hashval] = pre_transformed_input

    @abstractmethod
    def apply_output(self, taskmap: TaskMap, processed_output) -> TaskMap:
        pass

    @abstractmethod
    def process_inputs_into_outputs(self):
        """ Step 2 - implemented differently for simple vs batch augmenter """
        pass

    def gather_outputs(self, task_graphs):
        """ Step 3 """
        new_task_graphs = []

        for task_graph in task_graphs:
            if self.condition(task_graph):
                hash_val = task_graph.taskmap_id
                processed_taskgraph = self.apply_output(taskmap=task_graph, processed_output=self.output_dict[hash_val])
            else:
                processed_taskgraph = task_graph
            new_task_graphs.append(processed_taskgraph)

        return new_task_graphs

    def augment(self, task_graphs: List[TaskMap]) -> List[TaskMap]:
        """ Augmentation function """
        self.gather_inputs(task_graphs)
        self.process_inputs_into_outputs()
        return self.gather_outputs(task_graphs)


class AbstractSimpleTaskGraphAugmenter(AbstractTaskGraphAugmenter):

    @abstractmethod
    def process(self, taskmap: TaskMap) -> TaskMap:
        pass

    def process_inputs_into_outputs(self):
        """ Step 2 - Because not computational heavy can just loop over them """
        for hash_val in self.process_dict.keys():
            pre_transformed_input = self.process_dict[hash_val]
            processed_output = self.process(pre_transformed_input)
            self.output_dict[hash_val] = processed_output


class AbstractBatchTaskGraphAugmenter(AbstractTaskGraphAugmenter):

    @abstractmethod
    def batch_process(self, batch) -> List[TaskMap]:
        """ each batch consists of a list of tuples:
            (hash_val: str, pre_transformed_input)
        """
        pass

    def make_batches(self, batch_size=256):
        process_list = [(hash_val, self.process_dict[hash_val]) for hash_val in self.process_dict.keys()]
        batches = []
        for i in range(0, len(process_list), batch_size):
            batches.append(process_list[i:i + batch_size])
        return batches

    def process_inputs_into_outputs(self):
        """ Step 2 - Doing the processing with heavy GPU """
        batches = self.make_batches()
        for batch in batches:
            outputs = self.batch_process(batch)
            for (hash_val, sample), processed_output in zip(batch, outputs):
                self.output_dict[hash_val] = processed_output
