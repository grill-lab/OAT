import os
import shutil

from .dense_index_builder import DenseIndexBuilder
from .sparse_index_builder import SparseIndexBuilder


class ComposedIndexBuilder:
    def __init__(self, taskgraph_proto_path, taskgraph_proto_path_flattened, index_search_dir_sparse,
                 category_proto_path, index_objects_dir, index_search_dir_dense="", rebuild_objects_only=False):
        self.proto_paths = {"TaskMap": taskgraph_proto_path_flattened, "CategoryDocument": category_proto_path}
        self.taskgraph_proto_path = taskgraph_proto_path
        self.taskgraph_proto_path_flattened = taskgraph_proto_path_flattened
        self.index_objects_dir = index_objects_dir
        self.rebuild_objects_only = rebuild_objects_only
        if not rebuild_objects_only:
            self.index_search_dir_sparse = index_search_dir_sparse
            self.index_search_dir_dense = index_search_dir_dense

        self.index_objects_dir = index_objects_dir

    def __flatten_taskgraph_folder(self):
        domains_folders = os.listdir(self.taskgraph_proto_path)
        if os.path.isdir(self.taskgraph_proto_path_flattened):
            shutil.rmtree(self.taskgraph_proto_path_flattened)
        os.makedirs(self.taskgraph_proto_path_flattened, exist_ok=True)

        for domain in domains_folders:
            if os.path.isdir(os.path.join(self.taskgraph_proto_path, domain)):
                folder_path = os.path.join(self.taskgraph_proto_path, domain)
                files = os.listdir(folder_path)

                for file in files:
                    source_file = os.path.join(folder_path, file)
                    destination_file = os.path.join(self.taskgraph_proto_path_flattened, f"{domain}_{file}")
                    shutil.copy(source_file, destination_file)

    def run(self):

        self.__flatten_taskgraph_folder()

        if self.rebuild_objects_only:
            sparse_builder = SparseIndexBuilder(self.proto_paths, "", self.index_objects_dir)
            sparse_builder.run()
        else:
            sparse_builder = SparseIndexBuilder(self.proto_paths,
                                                self.index_search_dir_sparse,
                                                self.index_objects_dir)
            sparse_builder.run()

            if self.index_search_dir_dense != "":
                dense_builder = DenseIndexBuilder(self.proto_paths, self.index_search_dir_dense)
                dense_builder.run()
