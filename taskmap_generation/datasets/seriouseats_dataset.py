
from datasets.abstract_dataset import AbstractDataset
from utils import get_file_system
import json
import os

class SeriouseatsDataset(AbstractDataset):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.documents = self.__get_documents()

    def __get_documents(self):
        """ Read documents from dataset. """
        documents = []
        path = os.path.join(get_file_system(), 'taskmap_generation', 'seriouseats', 'serious_eats_docs.json')
        with open(path, 'r') as f:
            for line in f:
                doc = json.loads(line)
                documents.append(doc)
        return documents

    def generate_documents(self, k=1):
        """ Generator of k-sized chunks of documents for a given dataset. """
        yield from self.get_chunks(self.documents, k=k)

