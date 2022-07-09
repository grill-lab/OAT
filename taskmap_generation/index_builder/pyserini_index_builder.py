
import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from index_builder.abstract_index_builder import AbstractIndexBuilder


from google.protobuf.json_format import MessageToDict
from taskmap_pb2 import TaskMap
from utils import get_file_system
import subprocess
import stream
import json
import time
import os


class PyseriniIndexBuilder(AbstractIndexBuilder):

    def __parse_title(self, proto_message):
        """ Extract text contents from proto title and requirements """
        return proto_message.title

    def __parse_title_and_requirements(self, proto_message):
        """ Extract text contents from proto title and requirements """
        contents = ''
        contents += proto_message.title + '. '
        for requirement in proto_message.requirement_list:
            contents += requirement.name + ' '

        return contents

    def __parse_all(self, proto_message):
        """ Extract text content from proto. """
        contents = ''
        contents += proto_message.title + '. '
        for requirement in proto_message.requirement_list:
            contents += requirement.name + ' '
        for tag in proto_message.tags:
            contents += tag + ' '
        contents += proto_message.description + ''
        for step in proto_message.steps:
            contents += step.response.speech_text + ' '

        return contents

    def __get_protobuf_list_messages(self, path, proto_message):
        """ Retrieve list of protocol buffer messages from binary fire """
        return [d for d in stream.parse(path, proto_message)]

    def __build_doc(self, taskmap, how='all', dense=False):
        """ Build pyserini document from taskmap message. """
        if how == 'all':
            contents = self.__parse_all(taskmap)
        elif how == 'title':
            contents = self.__parse_title(taskmap)
        elif how == 'title+ingredients':
            contents = self.__parse_title_and_requirements(taskmap)
        else:
            print('error - not set how correctly')
            contents = self.__parse_all(taskmap)
        if not dense:
            return {
                "id": taskmap.taskmap_id,
                "contents": contents,
                "recipe_document_json": MessageToDict(taskmap),
            }
        else:
            return {
                "id": taskmap.taskmap_id,
                "text": contents,
                "contents": contents,
            }

    def __write_doc_file_from_lucene_indexing(self, input_dir, output_dir, dataset_name, how='all', dense=False):
        """ Write folder of pyserini json documents that represent taskmaps. """
        # Get list of files from 'in_directory'.
        file_names = [f for f in os.listdir(input_dir) if '.bin' in f]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for file_name in file_names:
            # Build in and out paths for file processing.
            in_path = os.path.join(input_dir, file_name)
            out_path = os.path.join(output_dir, dataset_name + '-' + file_name[:len(file_name) - 4] + '.jsonl')

            # Build list of pyserini documents.
            taskmap_list = self.__get_protobuf_list_messages(path=in_path, proto_message=TaskMap)
            docs_list = [self.__build_doc(taskmap, how=how, dense=dense)
                         for taskmap in taskmap_list]

            # Write to file.
            with open(out_path, 'w') as f:
                for doc in docs_list:
                    if 'text' in doc:
                        if len(doc['text']) > 0:
                            f.write(json.dumps(doc) + '\n')
                    else:
                        f.write(json.dumps(doc) + '\n')

    def __build_lucene_index(self, input_dir, output_dir):
        """ Builds an index with Pyserini """
        subprocess.run(["python3", "-m", "pyserini.index",
                        "-collection", "JsonCollection",
                        "-generator", "DefaultLuceneDocumentGenerator",
                        "-threads", "8",
                        "-input", input_dir,
                        "-index", output_dir,
                        "-storePositions", "-storeContents", "-storeRaw", "-storeDocvectors"])

    def __build_lucene_index_dense(self, input_dir, output_dir, cpu=True):
        """ Builds an index with Pyserini """

        if cpu:
            subprocess.run(["python3", "-m", "pyserini.encode", "input", "--corpus", input_dir, "--fields", "text",
                            "output", "--embedding", output_dir, "--to-faiss",
                            "encoder", "--encoder", "castorini/ance-msmarco-passage", "--fields", "text",
                            "--batch", "16", "--device", "cpu",
                            ])
        else:
            subprocess.run(["python3", "-m", "pyserini.encode", "input", "--corpus", input_dir, "--fields", "text",
                            "output", "--embedding", output_dir, "--to-faiss",
                            "encoder", "--encoder", "castorini/ance-msmarco-passage", "--fields", "text",
                            "--batch", "16",
                            ])

    def build_json_docs(self, input_dir, output_dir, dataset_name):
        """ Build index given directory of files containing taskmaps. """
        # Write Pyserini readable documents (i.e. json) to temporary folder.
        self.__write_doc_file_from_lucene_indexing(input_dir=input_dir,
                                                   output_dir=output_dir,
                                                   dataset_name=dataset_name,
                                                   how='all',
                                                   dense=False)

    def build_json_docs_dense(self, input_dir, output_dir, dataset_name):
        """ Build index given directory of files containing taskmaps. """

        self.__write_doc_file_from_lucene_indexing(input_dir=input_dir,
                                                   output_dir=output_dir,
                                                   dataset_name=dataset_name,
                                                   how='title',
                                                   dense=True)

    def build_index(self, input_dir, output_dir):
        # Build Pyserini index.
        self.__build_lucene_index(input_dir=input_dir,
                                  output_dir=output_dir)

    def build_index_dense(self, input_dir,  output_dir):
        # Build Pyserini index.
        self.__build_lucene_index_dense(input_dir=input_dir,
                                        output_dir=output_dir)
