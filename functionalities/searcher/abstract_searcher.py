import grpc
import os

from abc import ABC, abstractmethod
from searcher_pb2 import SearchQuery, SearchResults, TaskMapList, TaskmapIDs
from dangerous_task_pb2_grpc import DangerousStub


class AbstractSearcher(ABC):

    @abstractmethod
    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        pass

    @abstractmethod
    def retrieve_taskmap(self, ids: TaskmapIDs) -> SearchResults:
        pass

    @staticmethod
    def filter_dangerous_tasks(taskmap_list: TaskMapList, top_k: int) -> TaskMapList:
        external_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
        dangerous_task = DangerousStub(external_channel)

        taskmaps = []
        task_count = 0
        for taskmap in taskmap_list.candidates_union:
            dangerous_assessment = dangerous_task.dangerous_task_check(taskmap)
            if (not dangerous_assessment.is_dangerous) and (task_count < top_k):
                taskmaps.append(taskmap)
                task_count += 1

        safe_taskmap_list = TaskMapList()
        safe_taskmap_list.candidates.extend(taskmaps)

        return safe_taskmap_list
