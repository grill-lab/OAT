import os
import stream

from abc import ABC, abstractmethod
from taskmap_pb2 import TaskMap
from typing import List
from utils import get_file_system, logger


class AbstractTaskFilter(ABC):

    def __init__(self):
        self.passed_taskmap_count = 0
        self.failed_taskmap_count = 0
        self.failed_urls: List[str] = []
        self.filter_name = ""

    @staticmethod
    def save_failed_examples(class_name, failed_examples) -> None:
        dir_save_to = os.path.join(get_file_system(), "offline", "pipeline_stats", "filtering")
        if not os.path.isdir(dir_save_to):
            os.makedirs(dir_save_to, exist_ok=True)
        with open(os.path.join(dir_save_to, f"failed-{class_name}-examples.txt"), "w") as f:
            f.writelines('\n'.join(failed_examples))

    @abstractmethod
    def is_task_valid(self, taskmap: TaskMap) -> bool:
        pass

    @staticmethod
    def read_tasks_from_proto(path) -> List[TaskMap]:
        logger.info(path)
        return [d for d in stream.parse(path, TaskMap)]

    @staticmethod
    def write_tasks_to_proto(directory, filename, protobuf_list, buffer_size=1000) -> None:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)

    def get_filter_name(self) -> str:
        return self.filter_name

    def get_passed_count(self) -> int:
        return self.passed_taskmap_count

    def get_failed_count(self) -> int:
        return self.failed_taskmap_count

    def get_failed_taskmap_urls(self) -> List[str]:
        return self.failed_urls


