import torch
import os
import stream

from offline_pb2 import KnowledgeDocument
from marqo_tools import MarqoUtils


class MarqoKnowledgeIndexer:

    def __init__(self, knowledge_proto_path, index_name, batch_size, processes):
        self.device: int = -1 if not torch.cuda.is_available() else 0
        self.knowledge_proto_path = knowledge_proto_path
        self.index_name = index_name
        index_settings = {
            "index_defaults": {
                "text_preprocessing": {
                    "split_length": 6,
                    "split_overlap": 1,
                    "split_method": "sentence"
                }
            }
        }
        self.mq = MarqoUtils(index_settings=index_settings, batch_size=batch_size, processes=processes)

    @staticmethod
    def __get_protobuf_list_messages(path, proto_message):
        """ Retrieve list of protocol buffer messages from binary fire """
        return [d for d in stream.parse(path, proto_message)]

    def __parse_content(self, proto_message):
        """
            Args:
                proto_message: custom proto message, currently written for KnowledgeDocument.
            Returns:
                Proto fields as a well-formatted dictionary.
        """
        contents = {}
        if proto_message.date is not None or proto_message.date != "":
            contents["date"] = proto_message.date
        contents["title"] = proto_message.title
        contents["author"] = proto_message.author
        contents["contents"] = ". ".join([part for part in proto_message.contents])
        return contents

    def __build_proto_docs(self, input_dir, proto_message):
        """ Method to convert proto files in a directory to a list dictionaries
            Args:
                input_dir: path where the protos read in live
                proto_message: custom proto message
            Returns:
                a list of dictionaries with the content of the proto files
        """
        proto_list = []
        file_names = [f for f in os.listdir(input_dir) if '.bin' in f]
        for file_name in file_names:
            # Build in and out paths for file processing.
            in_path = os.path.join(input_dir, file_name)
            proto_list.extend(self.__get_protobuf_list_messages(in_path, proto_message=proto_message))
        docs_list = [self.__parse_content(proto_mes) for proto_mes in proto_list]
        return docs_list

    def build_index(self, input_dir, index_name):
        """ Method to run build of the knowledge corpus. Calls the Marqo utils to build the knowlegde index
                    (defined in `offline/marqo_tools.py`).
        """
        pre_processed_docs = self.__build_proto_docs(input_dir, proto_message=KnowledgeDocument)
        non_tensor_fields = ["author", "title"]
        self.mq.build_index(input_documents=pre_processed_docs, index_name=index_name,
                            non_tensor_fields=non_tensor_fields)

    def run(self):
        self.build_index(self.knowledge_proto_path, self.index_name)



