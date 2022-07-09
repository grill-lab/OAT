from abc import ABC, abstractmethod
from searcher_pb2 import SearchQuery, SearchResults, TaskMapList
from dangerous_task_pb2_grpc import DangerousStub

import grpc
import os

class AbstractSearcher(ABC):

    @abstractmethod
    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        pass

    @staticmethod
    def filter_dangerous_tasks(taskmap_list: TaskMapList, top_k: int) -> TaskMapList:
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        dangerous_task = DangerousStub(channel)

        l = []
        task_count = 0
        for taskmap in taskmap_list.candidates:
            dangerous_assessment = dangerous_task.dangerous_task_check(taskmap)
            if (not dangerous_assessment.is_dangerous) and (task_count < top_k):
                l.append(taskmap)
                task_count += 1

        safe_taskmap_list = TaskMapList()
        safe_taskmap_list.candidates.extend(l)

        return safe_taskmap_list
