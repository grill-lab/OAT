from compiled_protobufs.taskmap_pb2 import TaskMap
from compiled_protobufs.offline_pb2 import CategoryDocument
from google.protobuf.json_format import MessageToDict
import os

def parse_task(proto_message: TaskMap) -> str:
    """ Extract text content from taskmap proto. """
    contents = ''
    contents += proto_message.title + '. '
    for requirement in proto_message.requirement_list:
        contents += requirement.name + ' '
    for tag in proto_message.tags:
        contents += tag + ' '
    contents += proto_message.description + ''
    for step in proto_message.steps:
        contents += step.response.speech_text + ' '
    return contents.strip(",.grt").replace('\n', '')

def parse_category(proto_message: CategoryDocument) -> str:
    """ Extract text content from category proto. """
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

def build_doc_task(proto_message, include_proto=False) -> dict:
    """ Build pyserini document from taskmap message. """
    contents: str = parse_task(proto_message)
    if include_proto:
        return {
            "id": proto_message.taskmap_id,
            "contents": proto_message.taskmap_id,
            "document_json": MessageToDict(proto_message),
            "proto_type": "TaskMap"
        }
    else:
        return {
            "id": proto_message.taskmap_id,
            "contents": contents,
            "proto_type": "TaskMap"
        }
    
def build_doc_category(proto_message, include_proto=False) -> dict:
    """ Build pyserini document from taskmap message. """
    contents: str = parse_category(proto_message)
    if include_proto:
        return {
            "id": proto_message.cat_id,
            "contents": proto_message.taskmap_id,
            "document_json": MessageToDict(proto_message),
            "proto_type": "CategoryDocument",
        }
    else:
        return {
            "id": proto_message.cat_id,
            "contents": contents,
            "proto_type": "CategoryDocument",
        }