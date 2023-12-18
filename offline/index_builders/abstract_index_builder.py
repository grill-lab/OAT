from abc import ABC, abstractmethod


class AbstractIndexBuilder(ABC):

    @abstractmethod
    def build_doc(self, proto_message, include_proto):
        pass

    @abstractmethod
    def build_index(self, input_dir, output_dir):
        """ Build index given directory of files containing taskmaps. """
        pass

