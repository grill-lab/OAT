from index_builders.abstract_index_builder import AbstractIndexBuilder
from abc import abstractmethod
import subprocess


class PyseriniBM25Builder(AbstractIndexBuilder):
    
    def build_index(self, input_dir, output_dir):
        # Build Pyserini index.
        self.__build_lucene_index(input_dir=input_dir, output_dir=output_dir)

    @staticmethod
    def __build_lucene_index(input_dir, output_dir):
        """ Builds an index with Pyserini """
        subprocess.run(["python3", "-m", "pyserini.index",
                        "-collection", "JsonCollection",
                        "-generator", "DefaultLuceneDocumentGenerator",
                        "-threads", "8",
                        "-input", input_dir,
                        "-index", output_dir,
                        "-storePositions", "-storeContents", "-storeRaw", "-storeDocvectors"])