import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

import stream
import os


class Runner:
    """ Class that runs the taskmap generation process and builds index. """

    def __init__(self, config_dict):
        # Unpack config_dict.
        self.file_system_path = config_dict['file_system_path']
        self.datasets = config_dict['datasets']
        self.version = config_dict['version']
        self.IndexBuilder = config_dict['IndexBuilder']()
        self.dense_gen = config_dict.get('generate_dense_index', False)
        self.output_dir = config_dict.get("output_dir", "output")

    @staticmethod
    def __join_and_check(*args):
        path = os.path.join(*args)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        return path

    def __get_dir(self, dataset_config):
        dataset_path = self.__join_and_check(self.file_system_path,
                                             'taskmap_generation',
                                             dataset_config['dataset_name'])

        taskmap_dir = self.__join_and_check(dataset_path,
                                            'taskmap')
        return taskmap_dir

    def write_protobuf_list_to_file(self, path, protobuf_list, buffer_size=1000):
        """ Write list of Documents messages to binary file. """
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)

    def build_taskmaps(self):
        """ Generate folder of taskmaps stored within binary files. """
        print('*** building taskmaps ***')
        for dataset_config in self.datasets:
            print(dataset_config)
            # Init dataset_config dict.

            Dataset = dataset_config['Dataset']
            k = dataset_config['k']
            Convertor = dataset_config['Convertor']()
            dataset_kwargs = dataset_config.get('dataset_kwargs', {})

            taskmap_dir = self.__get_dir(dataset_config)

            chunk_counter = 0
            # Access chunks of k-sized documents for taskmap conversion.
            for chunk in Dataset(**dataset_kwargs).generate_documents(k=k):
                taskmap_list = []
                for document in chunk:
                    task_graph = Convertor.document_to_task_graph(document=document)
                    if Convertor.filter(task_graph):
                        taskmap_list.append(task_graph.to_proto())

                if len(taskmap_list) > 0:
                    # Write chunk of taskmaps to file.
                    print('---------------------')
                    print(f'len: {len(taskmap_list)}')
                    path = os.path.join(taskmap_dir, f'taskmaps_{chunk_counter}.bin')
                    print(f'writing taskmaps to file:{path}')
                    self.write_protobuf_list_to_file(path=path, protobuf_list=taskmap_list)
                    chunk_counter += 1

    def build_index(self):
        """ Generate index of taskmaps. """
        print('*** building index ***')

        output_temp_dir = self.__join_and_check(self.file_system_path,
                                                'taskmap_generation',
                                                'temp',
                                                self.output_dir)
        output_temp_dir_dense = self.__join_and_check(self.file_system_path,
                                                      'taskmap_generation',
                                                      'temp',
                                                      self.output_dir+"_dense")

        output_index_dir = self.__join_and_check(self.file_system_path,
                                                 'taskmap_generation',
                                                 'indexes',
                                                 self.output_dir)

        output_index_dir_dense = self.__join_and_check(self.file_system_path,
                                                       'taskmap_generation',
                                                       'indexes',
                                                       self.output_dir+"_dense")

        for dataset_config in self.datasets:
            print(dataset_config)

            # DATASET --> TASKMAP_DIR --> TEMP_DIR --> INDEX DIR

            dataset_name = dataset_config['dataset_name']
            taskmap_dir = self.__get_dir(dataset_config)

            # Generate json docs
            self.IndexBuilder.build_json_docs(input_dir=taskmap_dir,
                                              output_dir=output_temp_dir,
                                              dataset_name=dataset_name)
            if self.dense_gen:
                # Generate json docs dense
                self.IndexBuilder.build_json_docs_dense(input_dir=taskmap_dir,
                                                        output_dir=output_temp_dir_dense,
                                                        dataset_name=dataset_name)

        # Generate index.
        self.IndexBuilder.build_index(input_dir=output_temp_dir,
                                      output_dir=output_index_dir)
        if self.dense_gen:
            # Generate Dense index.
            self.IndexBuilder.build_index_dense(input_dir=output_temp_dir_dense,
                                                output_dir=output_index_dir_dense)
