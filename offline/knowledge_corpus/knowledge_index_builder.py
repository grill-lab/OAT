import os

from offline_pb2 import KnowledgeDocument
from utils import logger, get_file_system
from index_builders import PyseriniBM25Builder
from index_builders import build_json_docs
from google.protobuf.json_format import MessageToDict


class KnowledgeIndexBuilder(PyseriniBM25Builder):

    def __init__(self, knowledge_proto_path, knowledge_index_search_dir, knowledge_index_objects_dir):
        self.knowledge_proto_path = knowledge_proto_path
        self.index_search_dir = knowledge_index_search_dir
        self.index_objects_dir = knowledge_index_objects_dir
        self.output_temp_search_dir = os.path.join(get_file_system(), "offline", "knowledge_system_index_temp", "search")
        self.output_temp_objects_dir = os.path.join(get_file_system(), "offline", "knowledge_system_index_temp", "objects")
        
        if not os.path.exists(self.output_temp_search_dir):
            os.makedirs(self.output_temp_search_dir)
        if not os.path.exists(self.output_temp_objects_dir):
            os.makedirs(self.output_temp_objects_dir)

    @staticmethod
    def parse(proto_message):
        """
            Args:
                proto_message: custom proto message, currently written for KnowledgeDocument.
            Returns:
                Proto fields as a well-formatted dictionary.
        """
        contents = ". ".join([part for part in proto_message.contents])
        return contents

    def build_doc(self, proto_message, include_proto):
        contents = self.parse(proto_message)
        if include_proto:
            return {
                "id": proto_message.knowledge_id,
                "contents": contents,
                "document_json": MessageToDict(proto_message),
            }
        else:
            return {
                "id": proto_message.knowledge_id,
                "contents": contents,
            }

    def run(self):
        # build objects index
        build_json_docs(input_dir=self.knowledge_proto_path, output_dir=self.output_temp_objects_dir,
                        proto_message=KnowledgeDocument, include_proto=True, build_doc_function=self.build_doc)
        self.build_index(input_dir=self.output_temp_objects_dir, output_dir=self.index_objects_dir)

        # build search index
        build_json_docs(input_dir=self.knowledge_proto_path, output_dir=self.output_temp_search_dir,
                        proto_message=KnowledgeDocument, include_proto=False, build_doc_function=self.build_doc)
        self.build_index(input_dir=self.output_temp_search_dir, output_dir=self.index_search_dir)



