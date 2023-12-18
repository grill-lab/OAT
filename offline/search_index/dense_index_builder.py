import os
from utils import logger, get_file_system
from index_builders import PyseriniColbertBuilder, build_json_docs, write_protobuf_list_to_file

from compiled_protobufs.taskmap_pb2 import TaskMap
from compiled_protobufs.offline_pb2 import CategoryDocument

from .build_docs_helper import build_doc_task, build_doc_category

class DenseIndexBuilder(PyseriniColbertBuilder):

    def __init__(self, proto_paths, index_search_dir_dense):
        self.proto_paths = proto_paths
        self.index_search_dir_dense = index_search_dir_dense
        self.output_temp_search_dir = os.path.join(get_file_system(), "offline", "system_index_temp", "search")

    def build_doc(self, proto_message, include_proto):
        """ We are using a custom build_doc fuction which handles both Categories and Documents """
        pass

    def run(self):
        # build search index dense
        dense_temp_dir = os.path.join(self.output_temp_search_dir, "dense_temp")
        if not os.path.exists(dense_temp_dir):
            os.makedirs(dense_temp_dir)
        
        sorted_items = sorted(self.proto_paths.items(), key=lambda item: item[0])
        for proto_type, proto_path in sorted_items:
            if proto_type == "TaskMap":
                 build_json_docs(input_dir=proto_path, output_dir=dense_temp_dir,
                    proto_message=TaskMap, include_proto=False, build_doc_function=build_doc_task, 
                    out_files_begin_with = "taskmaps_", remove_prev = False)
            elif proto_type == "CategoryDocument":
                build_json_docs(input_dir=proto_path, output_dir=dense_temp_dir,
                    proto_message=CategoryDocument, include_proto=False, build_doc_function=build_doc_category,
                    out_files_begin_with = "categories_")
            else:
                raise Exception(f"Proto type {proto_type} not valid in dense index builder.")
                
        self.build_index(input_dir=dense_temp_dir, output_dir = self.index_search_dir_dense)
