import sys
import json

sys.path.append('../..')
sys.path.append('../../compiled_protobufs')


from utils.aws.composed_db import ComposedDB
from taskmap_pb2 import Session, ConversationTurn
from boto3.dynamodb.conditions import Key


def read_database(db, filter):
    retrieved_ids = db.scan_ids(scan_filter=filter)
    items_list = db.batch_get(retrieved_ids, decode=False)
    return items_list

if __name__ == "__main__":
    prefix = None
    database_url = 'http://dynamodb-local:8000'

    sessions_db = ComposedDB(
        proto_class=Session,
        url=database_url,
        # prefix=prefix,
        primary_key="session_id",
        sub_proto_config={
            "turn": {
                "proto_class": ConversationTurn,
                "primary_key": "id"
            },
        },
    )

    sessions_filter = (
        ~Key("session_id").begins_with("test_")
        # & ~Key("session_id").begins_with("local_")
    )

    items = read_database(sessions_db, sessions_filter)

    with open('sessions_dump.json', "w") as file:
        json.dump(items, file, indent=2)
