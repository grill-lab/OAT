import os
import json
import grpc

from searcher_pb2 import SearchQuery, SearchResults, TaskmapIDs
from .abstract_searcher import AbstractSearcher
from searcher_pb2_grpc import SearcherStub
from utils import logger, get_file_system, Downloader


class RemoteSearcher(AbstractSearcher):

    def retrieve_taskmap(self, ids: TaskmapIDs) -> SearchResults:
        return self.searcher_stub.retrieve_taskmap(ids)

    def __init__(self, environ_var: str):
        self.endpoint_var = environ_var
        channel = grpc.insecure_channel(os.environ.get(environ_var))
        self.searcher_stub = SearcherStub(channel)

        artefact_id = "tag_counts"
        downloader = Downloader()
        downloader.download([artefact_id])
        tags_count_path = downloader.get_artefact_path(artefact_id)
        with open(tags_count_path, "r") as json_file:
            tag_counts = json.load(json_file)
            self.tag_counts = {k.lower(): v for k, v in tag_counts.items()}

    def __sort_taskmap_tags(self, search_results: SearchResults) -> SearchResults:
        priority_tags = {
            "vegetarian",
            "gluten-free",
            "vegan",
            "dairy-free",
            "alcohol-free",
            "non-dairy",
            "make ahead",
            "5 ingredients or fewer",
            "one-pot wonders",
            "low calorie",
        }

        for candidate in search_results.candidate_list.candidates:
            if candidate.HasField("task"):
                tags = [tag.lower() for tag in candidate.task.tags]

                # Prioritize certain tags
                ordered_tags = []

                if len(candidate.task.steps) < 7:
                    ordered_tags.append("Easy")
                elif len(candidate.task.steps) < 13:
                    ordered_tags.append("Intermediate")
                else:
                    ordered_tags.append("Advanced")

                for tag in tags:
                    if tag in priority_tags:
                        ordered_tags.append(tag)

                # Sort the tags in descending order of their counts
                sorted_tags = sorted(tags, key=lambda tag: self.tag_counts.get(tag, 0), reverse=True)
                ordered_tags += sorted_tags

                uwanted_tags = {"kosher", "halal"}
                ordered_tags = [tag for tag in ordered_tags if not tag in uwanted_tags]

                # Filter out duplicates
                unique_set = set()
                unique_tags = [x for x in ordered_tags if not (x in unique_set or unique_set.add(x))]

                unique_tags = [tag.capitalize() for tag in unique_tags]
                del candidate.task.tags[:]
                candidate.task.tags.extend(unique_tags)

        return search_results

    def search_taskmap(self, query: SearchQuery) -> SearchResults:
        try:
            retrieved_result = self.searcher_stub.search_taskmap(query)
            search_result = self.__sort_taskmap_tags(retrieved_result)
        except grpc.RpcError:
            search_result = SearchResults()
            logger.warning("Endpoint did not respond. Is the Environment variable %s set?" % self.endpoint_var)

        return search_result
