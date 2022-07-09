
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from processing_steps.attributes_steps.abstract_attributes_step import AbstractAttributeStep
from task_graph.task_graph import TaskGraph
from utils import get_taskmap_id, get_credit_from_url


class StepWikihowAttributes(AbstractAttributeStep):

    DOC_TYPE = 'diy'
    DATASET = 'wikihow-offline'

    def __build_steps(self, document):
        """ Method for processing steps. """
        steps = []
        if 'steps' in document:
            if len(document['steps']) > 0:
                for step in document['steps']:
                    text = step['headline']
                    description = step['description']
                    if step['img']:
                        image = step['img']
                    else:
                        image = ''
                    steps.append((text, description, image))
                return steps

        if 'parts' in document:
            for part in document['parts']:
                for step in part['steps']:
                    text = step['headline']
                    description = step['description']
                    if step['img']:
                        image = step['img']
                    else:
                        image = ''
                    steps.append((text, description, image))
        return steps

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Add Wikihow attributes to task_graph. """

        # Dataset
        task_graph.set_attribute('dataset', self.DATASET)

        # Taskmap ID
        url = document['url']
        taskmap_id = get_taskmap_id(doc_type=self.DOC_TYPE, dataset=self.DATASET, url=url)
        task_graph.set_attribute('taskmap_id', taskmap_id)

        # URL
        task_graph.set_attribute('source_url', url)

        # Thumbnail URL
        steps = self.__build_steps(document=document)
        thumbnail_url = ''
        for step in steps:
            _, _, thumbnail_url_step = step
            if len(thumbnail_url_step) > 0:
                thumbnail_url = thumbnail_url_step
        if len(thumbnail_url) > 0:
            task_graph.set_attribute('thumbnail_url', thumbnail_url)

        # Title
        title = document['title']
        if title:
            task_graph.set_attribute('title', title)

        # Date
        date = document['time_updated']
        if date:
            task_graph.set_attribute('date', date)

        # Description
        description = document['title_description']
        if description:
            task_graph.set_attribute('description', description)

        # Rating out of 100
        rating_out_100 = document['rating']['helpful_percent']
        if rating_out_100:
            task_graph.set_attribute('rating_out_100', rating_out_100)

        # Rating count
        rating_count = document['rating']['n_votes']
        if rating_count:
            task_graph.set_attribute('rating_count', rating_count)

        # Tags
        tags = document['category_hierarchy']
        task_graph.tags = tags

        # FAQs
        for qa in document['QAs']:
            if len(qa) == 2:
                question, answer = qa[0], qa[1]
                if question and answer:
                    task_graph.add_faq(question=question.strip(),
                                       answer=answer.strip())

        # Extra
        tips_warnings = document['tips_warnings']
        for tip in tips_warnings:
            task_graph.add_extra_info(info_type='TIP', text=tip)

        # Domain name.
        domain_name = get_credit_from_url(url)
        if domain_name:
            task_graph.set_attribute('domain_name', domain_name)

        return task_graph

