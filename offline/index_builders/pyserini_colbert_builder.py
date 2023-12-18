from index_builders.abstract_index_builder import AbstractIndexBuilder
from utils import logger
from abc import abstractmethod

import subprocess
import torch


class PyseriniColbertBuilder(AbstractIndexBuilder):


    def build_index(self, input_dir, output_dir):
        # Build Pyserini index.
        self.__build_colbert_index(input_dir=input_dir, output_dir=output_dir)

    @staticmethod
    def __build_colbert_index(input_dir, output_dir):

        logger.info(f"GPU used for dense index: {torch.cuda.is_available()}")
        cpu = not torch.cuda.is_available()

        """ Builds a Colbert index with Pyserini """
        if cpu:
            subprocess.run(["python3", "-m", "pyserini.encode", "input", "--corpus", input_dir, "--fields", "text",
                            "output", "--embedding", output_dir, "--to-faiss",
                            "encoder", "--encoder", "castorini/tct_colbert-v2-msmarco", "--fields", "text",
                            "--batch", "16", "--device", "cpu",
                            ])
        else:
            subprocess.run(["python3", "-m", "pyserini.encode", "input", "--corpus", input_dir, "--fields", "text",
                            "output", "--embedding", output_dir, "--to-faiss",
                            "encoder", "--encoder", "castorini/tct_colbert-v2-msmarco", "--fields", "text",
                            "--batch", "16",
                            ])
