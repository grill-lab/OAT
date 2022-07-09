
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from abc import ABC, abstractmethod

class AbstractIndexBuilder(ABC):

    @abstractmethod
    def build_index(self, input_dir, output_dir):
        """ Build index given directory of files containing taskmaps. """
        pass
