from typing import List
from collections import Counter
from utils import logger


class StatsCollector:

    def get_stats_by_domain(self, urls: List[str]):
        """Returns the number of domains per url"""
        domains = [self.__filter_domain(url) for url in urls]
        domain_count = Counter(domains)
        logger.info(dict(domain_count.items()))
        return domain_count

    @staticmethod
    def __filter_domain(url: str) -> str:
        """Strips domain from the url"""
        # e.g. https://www.foodnetwork.com/recipes/grilled-strawberries-ala-mode-recipe-2117735 -> foodnetwork
        protocol, page = url.split("://")
        domain_name = page.replace("www.", "").split(".")[0]
        return domain_name

    
