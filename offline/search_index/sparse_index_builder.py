import os
from utils import logger, get_file_system
from index_builders import PyseriniBM25Builder
from index_builders import build_json_docs, write_protobuf_list_to_file

from compiled_protobufs.taskmap_pb2 import TaskMap
from compiled_protobufs.offline_pb2 import CategoryDocument

from .build_docs_helper import build_doc_task, build_doc_category


class SparseIndexBuilder(PyseriniBM25Builder):

    def __init__(self, proto_paths, index_search_dir_sparse, index_objects_dir):
        self.proto_paths = proto_paths
        self.index_search_dir_sparse = index_search_dir_sparse
        self.index_objects_dir = index_objects_dir
        self.output_temp_objects_dir = os.path.join(get_file_system(), "offline", "system_index_temp", "objects")
        if self.index_search_dir_sparse != "":
            self.output_temp_sparse_dir = os.path.join(get_file_system(), "offline", "system_index_temp", "sparse")


    def build_doc(self, proto_message, include_proto):
        """ We are using a custom build_doc fuction which handles both Categories and Documents """
        pass

    def run(self):
        # build taskmap objects index
        if not os.path.exists(self.output_temp_objects_dir):
            os.makedirs(self.output_temp_objects_dir)
        build_json_docs(input_dir=self.proto_paths["TaskMap"], output_dir=self.output_temp_objects_dir,
                        proto_message=TaskMap, include_proto = True, build_doc_function=build_doc_task)
        self.build_index(input_dir=self.output_temp_objects_dir, output_dir=self.index_objects_dir)

        if self.index_search_dir_sparse != "":
            # build sparse index
            if not os.path.exists(self.output_temp_sparse_dir):
                os.makedirs(self.output_temp_sparse_dir, exist_ok=True)

            sorted_items = sorted(self.proto_paths.items(), key=lambda item: item[0])
            for proto_type, proto_path in sorted_items:
                if proto_type == "TaskMap":
                    build_json_docs(input_dir = proto_path, output_dir = self.output_temp_sparse_dir,
                        proto_message = TaskMap, include_proto = False, build_doc_function = build_doc_task, 
                        out_files_begin_with = "taskmaps_", remove_prev = False)
                elif proto_type == "CategoryDocument":
                    build_json_docs(input_dir = proto_path, output_dir = self.output_temp_sparse_dir,
                        proto_message = CategoryDocument, include_proto = False, build_doc_function = build_doc_category,
                        out_files_begin_with = "categories_")
                else:
                    raise Exception(f"Proto type {proto_type} not valid in sparse index builder.")


            self.build_index(input_dir=self.output_temp_sparse_dir, output_dir=self.index_search_dir_sparse)
