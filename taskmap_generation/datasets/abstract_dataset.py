
from abc import ABC, abstractmethod


class AbstractDataset(ABC):

    def __init__(self, max_length=0):
        self.max_length = max_length

        assert max_length >= 0, "max_length parameter should be greater or equal to 0"

    def get_chunks(self, lst, k):
        """Yield successive chunks from n-sized lst."""
        length = self.max_length or len(lst)
        for i in range(0, length, k):
            yield lst[i:min(length, i + k)]

    @abstractmethod
    def generate_documents(self, k=1):
        """ Generator of k-sized chunks of documents for a given dataset. """
        pass
