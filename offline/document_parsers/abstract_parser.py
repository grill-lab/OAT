import hashlib
import re

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import dateutil.parser as dparser
from dateutil.parser import parserinfo

from utils import logger, get_credit_from_url
from document_pb2 import Step, CustomDocument
from task_graph import TaskGraph, RequirementNode, ExecutionNode
from taskmap_pb2 import ScreenInteraction, OutputInteraction, Image, Video

from typing import Optional, List


def check_for_multiple_sections(steps) -> (bool, list):
    """
        Args:
            - steps: EITHER
                        a linear list of CustomDocument.Steps() if the processing is done by our legacy parser
                     OR
                        a list of dictionaries containing a list of CustomDocument.Steps and a method name
                            [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]
        Returns:
            multiple_sections_found (BOOL), and EITHER a linear list of CustomDocument.Steps()
            OR the list of dictionaries containing a list of CustomDocument.Steps and a method name
    """

    if 'dict' in str(type(steps[0])):
        # it must be from wikihow for now
        if len(steps) > 1:
            return True, steps
        else:
            # there is just one sections, so process linearly
            return False, steps[0]["steps"]
    else:
        return False, steps

def process_execution_steps(steps: List[Step], task_graph):
    """ Creates a linear flow of execution nodes.
        Args:
            - steps: a linear list of CustomDocument.Steps()
            - task_graph: the task graph representing the task
        Returns:
            - start_stream_node_id: the ID of the node which is the first in the linear execution flow
            - end_stream_node_id: the ID of the node which is the last in the linear execution flow
    """
    prev_node_id: Optional[str] = None
    start_node_id = None
    for step in steps:
        output_interaction = OutputInteraction()

        if step.headline != "" and len(step.headline) > 10:
            output_interaction.speech_text = step.headline
            output_interaction.description = step.text
            output_interaction.screen.paragraphs.append(f'{step.headline}.')
            output_interaction.screen.paragraphs.append(step.text)  # maybe remove?
        else:
            output_interaction.speech_text = step.text
            output_interaction.screen.paragraphs.append(step.text)

        for i in step.image:
            image: Image = Image()
            image.path = i
            output_interaction.screen.image_list.append(image)

        if step.video != "":
            video = Video()
            video.hosted_mp4 = step.video
            output_interaction.screen.video.MergeFrom(video)

        output_interaction.screen.footer = step.headline
        output_interaction.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        node = ExecutionNode(response=output_interaction)

        current_node_id: str = task_graph.add_node(node)

        if start_node_id is None:
            start_node_id = current_node_id

        if prev_node_id is not None:
            task_graph.add_connection(prev_node_id, current_node_id)

        prev_node_id = current_node_id

    return start_node_id, prev_node_id


class AbstractParser(ABC):

    def __init__(self):
        self.soup = None

    @staticmethod
    def parse_time(time_str):
        class CustomParserInfo(parserinfo):
            HMS = [('h', 'hr', 'hrs', 'hour', 'hours'), ('m', 'min', 'mins', 'minute', 'minutes'),
                   ('s', 'second', 'seconds')]

        try:
            parsed_time = dparser.parse(time_str, fuzzy=True, parserinfo=CustomParserInfo())
            parsed_time_min = parsed_time.minute + parsed_time.hour * 60 + parsed_time.second / 60
            return parsed_time_min
        except:
            minutes = ('m', 'min', 'mins', 'minute', 'minutes')
            hours = ('h', 'hr', 'hrs', 'hour', 'hours')
            seconds = ('s', 'second', 'seconds')

            time_num = re.findall(r"\d+", time_str.strip())
            if len(time_num) > 0:
                final_time = 0
                time_int = int(time_num[0])
                for word in time_str.split(" "):
                    if word in minutes:
                        final_time = time_int
                    elif word in hours:
                        final_time = time_int * 60
                    elif word in seconds:
                        final_time = time_int / 60

                return final_time
            else:
                return 0

    @staticmethod
    def parse_date(date_str):
        return dparser.parse(date_str, fuzzy=True).strftime("%Y-%m-%d")

    @staticmethod
    def get_docid(url):
        """ Generate document unique identifier. """
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    @staticmethod
    def get_blank_doc():
        """ Generate blank document. """
        return CustomDocument()

    @staticmethod
    def clean_text(s):
        """ Standard cleaning of text. """
        return s.replace('\n', ' ').replace('\t', ' ').strip() if s is not None else s

    @staticmethod
    def get_soup_object(html):
        """ Build BeautifulSoup object from HTML. """
        return BeautifulSoup(html, 'html.parser')

    @abstractmethod
    def get_title(self):
        """ Parse title. """
        pass

    @abstractmethod
    def get_date(self):
        """ Parse title. """
        pass

    @abstractmethod
    def get_author(self):
        """ Parse author. """
        pass

    @abstractmethod
    def get_description(self):
        """ Parse descriptions. """
        pass

    @abstractmethod
    def get_image(self):
        """ Parse image. """
        pass

    @abstractmethod
    def get_video(self):
        """ Parse video. """
        pass

    @abstractmethod
    def get_duration_minutes_total(self):
        """ Parse duration. """
        pass

    @abstractmethod
    def get_tags(self):
        """ Parse tags. """
        pass

    @abstractmethod
    def get_requirements(self):
        """ Parse requirements. """
        pass

    @abstractmethod
    def get_serves(self):
        """ Parse serves. """
        pass

    @abstractmethod
    def get_rating_out_100(self):
        """ Parse rating. """
        pass

    @abstractmethod
    def get_steps(self):
        """ Parse steps. """
        pass

    @staticmethod
    def get_validity(url):
        """ Check if valid url / taskgraph """
        return True

    def parse(self, url, html):
        """  Parse HTML string into a TaskGraph representation
        Args:
            - url: the URL of the webpage fetched
            - html: the HTML of the webpage fetched
        Returns:
            a TaskGraph representing the parsed task from the website
        """
        """  Parse HTML string. """
        # check that valid url
        if not self.get_validity(url):
            return

        # Init taskgraph proto
        task_graph = TaskGraph()

        # Domain name.
        domain_name = get_credit_from_url(url)
        if domain_name:
            task_graph.set_attribute('domain_name', domain_name)

        # Dataset
        task_graph.set_attribute('dataset', 'common-crawl')

        # Build soup from HTML string.
        self.soup = self.get_soup_object(html=html)

        task_graph.set_attribute("source_url", url)
        if self.get_docid(url=url):
            task_graph.set_attribute("taskmap_id", self.get_docid(url=url))

        if self.get_title():
            task_graph.set_attribute("title", self.get_title())
        else:
            logger.info('No title')
            return

        if self.get_description():
            task_graph.set_attribute("description", self.get_description())
        if self.get_date():
            task_graph.set_attribute("date", self.get_date())
        if self.get_author():
            task_graph.set_attribute("author", self.get_author())
        if self.get_image():
            task_graph.set_attribute("thumbnail_url", self.get_image())
        if self.get_serves():
            task_graph.set_attribute("serves", self.get_serves())
        if self.get_rating_out_100():
            task_graph.set_attribute("rating_out_100", self.get_rating_out_100())
        if self.get_duration_minutes_total():
            task_graph.set_attribute("total_time_minutes", self.get_duration_minutes_total())

        if self.get_requirements() == [] and 'wikihow' not in url:
            logger.info('No requirements')
            return
        # requirements how to properly split the parts
        for ingredient in self.get_requirements():
            if ingredient != '':
                node = RequirementNode(
                    name=ingredient,
                    req_type='SOFTWARE',
                    amount=' ',
                    linked_taskmap_id=''
                )
                task_graph.add_node(node)

        for t in self.get_tags():
            task_graph.tags.append(t.text)

        steps = self.get_steps()
        if len(steps) == 0:
            logger.info('No steps')
            return

        methods_found, steps = check_for_multiple_sections(steps)

        if methods_found:
            if steps[0]['method_name'] is not None and "Part" in steps[0]["method_name"]:
                # create_parts(steps, task_graph)
                all_parts_step_list = []
                for part in steps:
                    all_parts_step_list.extend(part["steps"])
                _, _ = process_execution_steps(steps=all_parts_step_list, task_graph=task_graph)
            else:
                # create_methods(steps, task_graph)
                _, _ = process_execution_steps(steps=steps[0]["steps"], task_graph=task_graph)
        else:
            # process the steps linearly
            _, _ = process_execution_steps(steps, task_graph)

        return task_graph
