
import sys
sys.path.insert(0, '/shared')

from datasets.abstract_dataset import AbstractDataset

from utils import get_file_system
import json
import os

class WikihowDataset(AbstractDataset):

    def __init__(self, categories=[], **kwargs):
        super().__init__(**kwargs)
        self.wiki_categories = set(categories)
        self.documents = self.__get_documents()

    def __get_documents(self):
        """ Read documents from dataset. """
        requirements_path = os.path.join(get_file_system(), 'taskmap_generation', 'wikihow', 'wikihow_upen_req.jsonl')
        requirements_mapping = {}
        with open(requirements_path, 'r') as f_req:
            for line in f_req:
                url_req = json.loads(line)
                url = url_req['url']
                requirements_mapping[url] = url_req['requirements']

        path = os.path.join(get_file_system(), 'taskmap_generation', 'wikihow', 'wikihow_upen.jsonl')
        documents = []
        with open(path, 'r') as f:
            for line in f:
                try:
                    document = json.loads(line)
                except:
                    continue
                document['requirements'] = requirements_mapping.get(document['url'], [])

                # If non empty intersection add document
                if self.wiki_categories == set() or\
                        self.wiki_categories.intersection(set(document['category_hierarchy'])):
                    documents.append(document)
        return documents

    def generate_documents(self, k=1):
        """ Generator of k-sized chunks of documents for a given dataset. """
        yield from self.get_chunks(self.documents, k=k)
