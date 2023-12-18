from .filter_abstract import AbstractTaskFilter
from typing import List
from taskmap_pb2 import TaskMap


class DuplicatesFilter(AbstractTaskFilter):
    """Filters duplicate tasks"""

    def __init__(self):
        super().__init__()
        self.passed_taskmap_count = 0
        self.failed_taskmap_count = 0
        self.failed_urls: List[str] = []
        self.filter_name = "duplicates-filter"
        self.visited_tasks = set()

    def is_task_valid(self, taskmap: TaskMap) -> bool:
        task_title = taskmap.title
        is_valid = task_title not in self.visited_tasks
        if is_valid:
            self.passed_taskmap_count += 1
            self.visited_tasks.add(task_title)
        else:
            self.failed_taskmap_count += 1
            self.failed_urls.append(taskmap.source_url)
        return is_valid
