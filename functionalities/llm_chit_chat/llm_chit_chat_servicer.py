from compiled_protobufs.llm_pb2 import LLMChitChatRequest
from compiled_protobufs.chitchat_classifier_pb2 import ChitChatResponse
from compiled_protobufs.llm_pb2_grpc import LLMChitChatServicer, add_LLMChitChatServicer_to_server
from . import DefaultLLMChitChat


class Servicer(LLMChitChatServicer):

    def __init__(self):
        self.chit_chat_model = DefaultLLMChitChat()

    def generate_chit_chat(self, query: LLMChitChatRequest, context) -> ChitChatResponse:
        return self.chit_chat_model.generate_chit_chat(query)
