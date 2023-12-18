import os

from utils import get_file_system
from index_builders import PyseriniBM25Builder, build_json_docs, filter_duplicates
from compiled_protobufs.offline_pb2 import CategoryDocument
from google.protobuf.json_format import MessageToDict


class CategoryIndexBuilder(PyseriniBM25Builder):
    def __init__(self, proto_path, objects_index_dir):
        self.proto_path = proto_path
        self.output_temp_dir = os.path.join(get_file_system(), "offline", "category_temp")
        self.output_index_objects = objects_index_dir

    @staticmethod
    def parse(proto_message):
        contents = ''
        contents += proto_message.title + '. '
        for query in proto_message.alternate_queries:
            contents += query + ' '

        for sub_category in proto_message.sub_categories:
            contents += sub_category.title + " "

            for cand in sub_category.candidates:
                contents += cand.title

            for query in sub_category.alternate_queries:
                contents += ' ' + query
        return contents

    def build_doc(self, proto_message, include_proto=True):
        contents = self.parse(proto_message)
        if include_proto:
            return {
                "id": proto_message.cat_id,
                "contents": contents,
                "category_document_json": MessageToDict(proto_message)
            }
        return {
            "id": proto_message.cat_id,
            "contents": contents,
        }

    def run(self):
        if not os.path.isdir(os.path.join(get_file_system(), "offline/category_index")):
            os.makedirs(os.path.join(get_file_system(), "offline/category_index"), exist_ok=True)

        # build object index
        if not os.path.exists(self.output_index_objects):
            os.makedirs(self.output_index_objects, exist_ok=True)

        build_json_docs(input_dir=self.proto_path, output_dir=self.output_temp_dir,
                        proto_message=CategoryDocument, include_proto=True, build_doc_function=self.build_doc)
        filter_duplicates(input_dir=self.output_temp_dir)
        self.build_index(input_dir=self.output_temp_dir, output_dir=self.output_index_objects)
