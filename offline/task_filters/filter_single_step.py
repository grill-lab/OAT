from .filter_abstract import AbstractTaskFilter
from typing import List
from taskmap_pb2 import TaskMap


class SingleStepFilter(AbstractTaskFilter):
    """Filters TaskGraphs which contains 1 or 0 steps."""

    def __init__(self):
        super().__init__()
        self.filter_name = "single-step-filter"
    
    def is_task_valid(self, taskmap: TaskMap) -> bool:
        is_valid = len(taskmap.steps) > 1
        if is_valid:
            self.passed_taskmap_count += 1
        else:
            self.failed_taskmap_count += 1
            self.failed_urls.append(taskmap.source_url)
        return is_valid
