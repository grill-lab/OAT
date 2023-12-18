import os

from .filter_abstract import AbstractTaskFilter
from .stats_collector import StatsCollector
from utils import get_file_system, logger
from taskmap_pb2 import TaskMap

from typing import List


class ComposedFilter(AbstractTaskFilter):
    """ Collects all TaskGraph filters and measures statistics regarding filtering """

    def __init__(self, path_in: str, path_out: str, task_filters: List[AbstractTaskFilter]):
        super().__init__()
        if not os.path.exists(path_in):
            raise Exception(f"path_in = {path_in} is not a directory (ComposedFilter).")
        if len(task_filters) == 0:
            raise Exception(f"No filters instantiated (ComposedFilter)")

        self.path_in = path_in
        self.path_out = path_out
        # collect all filters
        self.task_filters = [filter_class() for filter_class in task_filters]
        self.filter_name = "composed-filter"
        self.failed_urls = []
        self.passed_urls = []
        self.passed_taskmap_count = 0
        self.failed_taskmap_count = 0

    def run(self) -> None:
        """ Batch Retrieval Filtering """
        if not os.path.isdir(self.path_out):
            os.makedirs(self.path_out, exist_ok=True)
        for domain in os.listdir(self.path_in):
            if os.path.isdir(os.path.join(self.path_in, domain)):
                domain_path = os.path.join(self.path_in, domain)
                for batch_name in os.listdir(domain_path):
                    if batch_name.endswith(".bin"):
                        self.__filter_tasks(domain, batch_name)
                        logger.info(f"Filtered batch: {batch_name}")
        self.__save_stats()

    def __filter_tasks(self, domain: str, batch_name: str) -> None:
        taskmaps = self.read_tasks_from_proto(os.path.join(self.path_in, domain, batch_name))
        logger.info(len(taskmaps))
        filtered_tasks = [taskmap for taskmap in taskmaps if self.is_task_valid(taskmap)]
        filename_saved = "filtered_tasks_" + batch_name
        domain_path = os.path.join(self.path_out, domain)
        self.write_tasks_to_proto(domain_path, filename_saved, filtered_tasks)

    def __save_stats(self):
        """Save measurements"""
        stats = self.__get_stats()
        saved_details = []
        for filter_name, info in sorted(stats.items()):
            saved_details.append(f"filter name: {filter_name}")
            for attribute_name, attribute_val in info.items():
                if attribute_name != "failed urls":
                    saved_details.append(f"{attribute_name}: {attribute_val}")
            saved_details.append("")  # add whitespace

        stats_folder = os.path.join(get_file_system(), "offline", "pipeline_stats", "filtering")
        if not os.path.exists(stats_folder):
            os.makedirs(stats_folder)
        filename = "stats.txt"
        with open(os.path.join(stats_folder, filename), "w") as f:
            f.writelines('\n'.join(saved_details))

        """Add stats by domain"""
        stats_collector = StatsCollector()
        passed_stats = stats_collector.get_stats_by_domain(self.passed_urls)
        failed_stats = stats_collector.get_stats_by_domain(self.failed_urls)
        combined_stats = stats_collector.get_stats_by_domain(self.passed_urls + self.failed_urls)
        saved_lines = []
        for key, value in sorted(combined_stats.items()):
            saved_lines.append(
                f'domain: {key}, total: {value}, passed: {passed_stats[key]}, failed: {failed_stats[key]}')
        with open(os.path.join(stats_folder, filename), "a+") as f:
            f.writelines("\n".join(saved_lines))

        """Save failed urls"""
        for filter_name, info in sorted(stats.items()):
            path_saved = os.path.join(stats_folder, filter_name + ".txt")
            with open(path_saved, "w") as f:
                f.writelines('\n'.join(info["failed urls"]))

        logger.info(f"Saved filter stats at {stats_folder}")

        """Save failed dangerous examples"""
        for t_filter in self.task_filters:
            if t_filter.get_filter_name() == "dangerous-filter":
                t_filter.save_failed_examples("dangerous-filter", t_filter.failed_urls)

    def __get_stats(self) -> dict[str:dict[str:any]]:
        """Collect measurements from filters"""
        stats = {}
        for specific_filter in self.task_filters:
            filter_name = specific_filter.get_filter_name()
            passed_count = specific_filter.get_passed_count()
            failed_count = specific_filter.get_failed_count()
            failed_urls = specific_filter.get_failed_taskmap_urls()
            stats[filter_name] = {
                "passed tasks": passed_count,
                "failed tasks": failed_count,
                "failed urls": failed_urls,
            }

        filter_name = self.get_filter_name()
        passed_count = self.get_passed_count()
        failed_count = self.get_failed_count()
        failed_urls = self.get_failed_taskmap_urls()
        stats[filter_name] = {
            "passed tasks": passed_count,
            "failed tasks": failed_count,
            "failed urls": failed_urls,
        }

        return stats

    def is_task_valid(self, taskmap: TaskMap) -> bool:
        task_checks: List[bool] = [check.is_task_valid(taskmap) for check in self.task_filters]
        is_valid: bool = all(task_checks)
        if is_valid:
            self.passed_taskmap_count += 1
            self.passed_urls.append(taskmap.source_url)
        else:
            self.failed_taskmap_count += 1
            self.failed_urls.append(taskmap.source_url)
        return is_valid
