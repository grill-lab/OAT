from utils import logger
import os
import stream
import shutil

from typing import List

from taskmap_pb2 import TaskMap
import torch


class AugmentationsIterator:
    
    def __init__(self, taskgraph_proto_path, augmented_taskgraph_proto_path, augmenters, augment_domains):
        self.taskgraph_proto_path = taskgraph_proto_path
        self.augmented_taskgraph_proto_path = augmented_taskgraph_proto_path
        self.augmenters = augmenters
        self.augment_domains = augment_domains
    
    def run(self):
        self.augment_taskgraphs()
    
    def __write_protobuf_list_to_file(self, path, protobuf_list, buffer_size=1000):
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)
        
    def __read_protobuf_list_from_file(self, path,  proto_message):
        return [d for d in stream.parse(path, proto_message)]

    def augment_taskgraphs(self):
        if torch.cuda.is_available():
            logger.info("Using cuda...")

        if not os.path.exists(self.augmented_taskgraph_proto_path):
            os.makedirs(self.augmented_taskgraph_proto_path, exist_ok=True)
        
        if len(self.augment_domains) == 0:
            domain_names = os.listdir(self.taskgraph_proto_path)
        else:
            domain_names = [config["file_path"] for config in self.augment_domains]

        for domain_name in domain_names:
            domain_path = os.path.join(self.taskgraph_proto_path, domain_name)
            domain_path_save_to = os.path.join(self.augmented_taskgraph_proto_path, domain_name)
            if os.path.isdir(domain_path_save_to):
                shutil.rmtree(domain_path_save_to)
            os.makedirs(domain_path_save_to, exist_ok=True)
            
            if not os.path.isdir(domain_path):
                os.makedirs(domain_path, exist_ok=True)
                
            for batch in os.listdir(domain_path):
                # if batch.endswith(".bin") and not "taskgraphs_" + batch.split("_")[-1] in os.listdir(self.augmented_taskgraph_proto_path):
                task_maps = self.__read_protobuf_list_from_file(os.path.join(domain_path, batch), TaskMap)
                augmented_taskmaps = []
                for augmenter_class in self.augmenters:
                    augmenter = augmenter_class()
                    augmented_taskmaps = augmenter.augment(task_maps)
                    task_maps = augmented_taskmaps
                filename = "taskgraphs_" + batch
                self.__write_protobuf_list_to_file(os.path.join(domain_path_save_to, filename), task_maps)
