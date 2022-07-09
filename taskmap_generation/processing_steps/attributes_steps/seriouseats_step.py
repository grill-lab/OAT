
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from processing_steps.attributes_steps.abstract_attributes_step import AbstractAttributeStep
from task_graph.task_graph import TaskGraph
from utils import get_taskmap_id, get_credit_from_url


class StepSeriouseatsAttributes(AbstractAttributeStep):

    DOC_TYPE = 'cooking'
    DATASET = 'seriouseats'

    def update_task_graph(self, document, task_graph: TaskGraph) -> TaskGraph:
        """ Add Wikihow attributes to task_graph. """

        # Dataset
        task_graph.set_attribute('dataset', self.DATASET)

        # Taskmap ID
        url = str(document['source_url'])
        taskmap_id = get_taskmap_id(doc_type=self.DOC_TYPE, dataset=self.DATASET, url=url)
        task_graph.set_attribute('taskmap_id', taskmap_id)

        # URL
        task_graph.set_attribute('source_url', str(url))

        # Thumbnail URL
        image = document['image']
        if len(image) > 0:
            task_graph.set_attribute('thumbnail_url', str(image[0]))

        # Title
        title = str(document['title'])
        if title:
            task_graph.set_attribute('title', title)

        # Description
        description = str(document['description'])
        if description:
            task_graph.set_attribute('description', description)

        ratings = document['ranking_out_100']
        if ratings:
            # Rating out of 100
            task_graph.set_attribute('rating_count', int(ratings))

        # Tags
        tags = document['tags']
        if len(tags) > 0 :
            task_graph.tags = tags

        # Domain name.
        task_graph.set_attribute('domain_name', 'seriouseats')

        # Author.
        author = document['author']
        if author:
            task_graph.set_attribute('author', author)

        return task_graph

