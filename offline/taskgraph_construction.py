import os
import stream

from offline_pb2 import HTMLDocument
from utils import logger
from converter import Converter


class TaskgraphConstruction:
    def __init__(self, html_proto_path, taskgraph_proto_path, parsers, parse_domains):
        self.html_proto_path = html_proto_path
        self.taskgraph_proto_path = taskgraph_proto_path
        self.parsers = parsers
        self.which_domains = parse_domains
    
    def run(self):
        self.load_taskgraphs_from_html()

    @staticmethod
    def __write_protobuf_list_to_file(path, protobuf_list, buffer_size=1000):
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)

    @staticmethod
    def __read_protobuf_list_from_file(path,  proto_message):
        return [d for d in stream.parse(path, proto_message)]
    
    def load_taskgraphs_from_html(self):
        if not os.path.exists(self.taskgraph_proto_path):
            os.makedirs(self.taskgraph_proto_path, exist_ok=True)
        
        if len(self.which_domains) == 0:
            domain_names = os.listdir(self.html_proto_path)
        else:
            domain_names = [parser_config["file_path"] for parser_config in self.which_domains]

        for domain_name in domain_names[1:]:
            
            html_filepath = os.path.join(self.html_proto_path, domain_name)
            domain_task_path = os.path.join(self.taskgraph_proto_path, domain_name)

            if not os.path.isdir(domain_task_path):
                os.makedirs(domain_task_path, exist_ok=True)

            if not os.path.isdir(html_filepath):
                os.makedirs(html_filepath, exist_ok=True)

            for batch in os.listdir(html_filepath):
                filename = "taskgraphs_" + batch.split("_")[-1]
                taskgraph_protos = []
                logger.info(f"Reading from {os.path.join(self.html_proto_path, domain_name, batch)}")
                webpages = self.__read_protobuf_list_from_file(os.path.join(self.html_proto_path,domain_name, batch), HTMLDocument)
                for webpage in webpages:
                    c = Converter(self.parsers)
                    c.convert_htmls(webpage.url, webpage.html)
                    if c.get_taskgraph_proto() is not None:
                        taskgraph_protos.append(c.get_taskgraph_proto())
                    logger.info(f'{webpage.url} to taskgraph')
                self.__write_protobuf_list_to_file(os.path.join(self.taskgraph_proto_path, domain_name, filename), taskgraph_protos)
