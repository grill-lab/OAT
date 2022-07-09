import sys
import json

sys.path.append('../..')
sys.path.append('../../compiled_protobufs')

from utils import ComposedDB
from boto3.dynamodb.conditions import Key
from searcher_pb2 import SearchLog


def read_database(db, filter):
    retrieved_ids = db.scan_ids(scan_filter=filter)
    items_list = db.batch_get(retrieved_ids, decode=False)
    return items_list


prefix = 'production'
database_url = None

search_logs_db = ComposedDB(
    proto_class=SearchLog,
    url=database_url,
    prefix=prefix,
    primary_key="id",
    sub_proto_config={}
)

search_logs_filter = (
    ~Key("id").begins_with("amzn1.")
    & ~Key("id").begins_with("test_")
    & ~Key("id").begins_with("local_")
)

search_logs_list = read_database(search_logs_db, search_logs_filter)

with open('search_logs.json', "w") as file:
    json.dump(search_logs_list, file, indent=2)
