import os
from utils import get_file_system
from taskmap_pb2 import TaskMap
from .abstract_searcher import AbstractSearcher
from searcher_pb2 import SearchQuery, SearchResults, TaskMapList, TaskmapIDs


class FixedSearcher(AbstractSearcher):
    def __init__(self, file_list):
        folder_path = os.path.join(get_file_system(), 'custom_taskmaps')

        self.taskmap_list = TaskMapList()
        for file_name in file_list:
            with open(os.path.join(folder_path, file_name), 'rb') as f:
                taskmap = TaskMap()
                taskmap.ParseFromString(f.read())
                self.taskmap_list.candidates.append(taskmap)

    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        response: SearchResults = SearchResults()

        response.taskmap_list.CopyFrom(self.taskmap_list)
        return response

    def retrieve_taskmap(self, ids: TaskmapIDs) -> SearchResults:
        pass