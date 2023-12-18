import stream
import os
import torch

from utils import logger
from taskmap_pb2 import TaskMap
from marqo_tools import MarqoUtils
from task_graph import TaskGraph


class TaskContextConstruction:
    def __init__(self, taskgraph_proto_path, index_name, batch_size, processes):
        self.taskgraph_proto_path = taskgraph_proto_path
        self.device: int = -1 if not torch.cuda.is_available() else 0
        self.index_name = index_name
        index_settings = {
            "index_defaults": {
                "model": "flax-sentence-embeddings/all_datasets_v4_MiniLM-L6",
                "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 3,
                        "split_overlap": 1,
                        "split_method": "sentence"
                                    },
            },
        }
        self.mq = MarqoUtils(index_settings=index_settings, batch_size=batch_size, processes=processes)

    def __write_protobuf_list_to_file(self, path, protobuf_list, buffer_size=1000):
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)

    def __read_protobuf_list_from_file(self, path, proto_message):
        return [d for d in stream.parse(path, proto_message)]

    @staticmethod
    def strip_newlines(text):
        return text.replace('\n', " ").replace("  ", " ")

    def __build_context(self, task_graph: TaskGraph):
        """
        Creates the optimal context given to the model for inference
        """
        title = f"The title of this is {self.strip_newlines(task_graph.title)}.\n"
        author = f"The instructions were created by the author: {self.strip_newlines(task_graph.author)}.\n"
        time = f"The total time in minutes to work through the instructions is: {task_graph.total_time_minutes} minutes.\n"
        rating = f"The instruction has a rating of {task_graph.rating_out_100} out of 100\n."
        servings = f"The instructions make up a serving of {self.strip_newlines(task_graph.serves)}.\n"
        description = f"The description of the instructions is: {self.strip_newlines(task_graph.description)}\n"

        steps = []
        index = 1
        for key, value in task_graph.node_set.items():
            if value.__class__.__name__ == "ExecutionNode":
                steps.append(f'{index}. ' + value.response.speech_text)
                index += 1
        string_steps = '\n'.join(steps)

        requirements = 'Requirements/Ingredients: '
        for key, value in task_graph.node_set.items():
            if value.__class__.__name__ == "RequirementNode":
                requirements += value.amount + ' ' + value.name + '; '

        document = title + author + time + rating + servings + description + string_steps

        return document

    def load_taskgraphs_from_file(self):
        taskmaps = []
        for domain in os.listdir(self.taskgraph_proto_path):
            for batch in os.listdir(os.path.join(self.taskgraph_proto_path, domain)):
                logger.info(os.path.join(self.taskgraph_proto_path, batch))
                taskmaps.extend(self.__read_protobuf_list_from_file(os.path.join(self.taskgraph_proto_path, domain, batch), TaskMap))
        return taskmaps

    def build_contexts(self, taskmaps):
        processed_taskmaps = []
        ids = []
        for taskmap in taskmaps:
            task_graph = TaskGraph(taskmap)
            context = self.__build_context(task_graph)
            id = taskmap.taskmap_id
            processed_taskmaps.append((context, id))
        return processed_taskmaps

    def build_index(self, index_name):
        taskmaps = self.load_taskgraphs_from_file()
        contexts = self.build_contexts(taskmaps)
        self.mq.build_index(input_documents=[{"document": context, "taskmap_id": id} for (context, id) in contexts], index_name=index_name, non_tensor_fields=["taskmap_id"])

    def run(self):
        self.build_index(index_name=self.index_name)


