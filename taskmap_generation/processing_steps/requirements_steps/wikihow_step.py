
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.task_graph import TaskGraph
from task_graph.nodes.requirement_node import RequirementNode
from processing_steps.requirements_steps.abstract_requirements_step import AbstractRequirementsStep

from bs4 import BeautifulSoup
import requests

class StepWikihowRequirements(AbstractRequirementsStep):

    def __get_soup_object(self, url):
        """
        Build BeautifulSoup object for a given URL.
        :param url: Website being scraped URL(str).
        :return: BeautifulSoup object with HTML parser (BeautifulSoup object).
        """
        req = requests.get(url)
        return BeautifulSoup(req.content, 'html.parser')

    def __get_wikihow_requirements(self, url):
        """ """
        soup = self.__get_soup_object(url)
        requirements = []
        tun_object = soup.find(id='thingsyoullneed')
        if tun_object:
            # Loop of ingredient objects to add full list.
            for child in tun_object.find_all('li'):
                requirements.append(child.text.strip())
        return requirements

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Add Wikihow requirements to task_graph. """
        try:
            requirements = document['requirements']

            for r in requirements:
                node = RequirementNode(
                    name=r,
                    req_type='HARDWARE',
                    amount='',
                    linked_taskmap_id=''
                )
                task_graph.add_node(node)
        except:
            print('Error parsing Wikidata URLs.')

        return task_graph