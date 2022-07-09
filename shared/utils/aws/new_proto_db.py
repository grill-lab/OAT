import boto3
from typing import List, Dict, Iterator, Iterable, Tuple
from datetime import datetime
from botocore.exceptions import ClientError
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict, ParseDict
from utils import timeit
import time
from .decimal_ops import convert_decimals_to_float, convert_floats_to_decimals
from itertools import islice

from boto3.dynamodb.types import TypeDeserializer


def init_table(table_name, primary_key, url):
    dynamodb = boto3.resource('dynamodb', endpoint_url=url, region_name='us-east-1')

    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': primary_key,
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': primary_key,
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 50,
                'WriteCapacityUnits': 50
            }
        )
    except ClientError as e:
        table = dynamodb.Table(table_name)

    table.wait_until_exists()

    return table


def grouper(iterable: Iterable[str], n: int) -> Iterable[Tuple[str]]:
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, n))
        if not chunk:
            return
        yield chunk


def check_attr(proto_class, param: str):
    fake_obj = proto_class()
    assert hasattr(fake_obj, param), f"configured parameter {param} is " \
                                     f"not an attribute of the message {proto_class.__name__}"


class ProtoDB:

    def __init__(self,
                 proto_class,
                 primary_key: str = 'id',
                 url: str = None,
                 prefix: str = "Undefined"):

        assert issubclass(proto_class, Message), "ProtoDB works only with protobuf classes"

        table_name = prefix + "_" + proto_class.__name__
        self.proto_class = proto_class

        check_attr(proto_class, primary_key)
        self.primary_key = primary_key

        self.deserializer = TypeDeserializer()
        self.__table = init_table(table_name, primary_key, url)
        self.__client = boto3.client('dynamodb', endpoint_url=url, region_name='us-east-1')

    def _encode_dict(self, obj: Message) -> dict:
        """
            Protected method to specify operations to perform before sending the Proto Object to the DB
        """
        assert isinstance(obj, self.proto_class), f"expecting object of type {self.proto_class}," \
                                                  f"but got {type(obj)}"

        payload = MessageToDict(obj, preserving_proto_field_name=True)
        payload = convert_floats_to_decimals(payload)
        payload['last_modified'] = datetime.now().isoformat()

        return payload

    def _decode_dict(self, message_dict: dict) -> dict:
        """
            Protected method to specify operations to decode the object before parsing to proto
        """
        message_dict = convert_decimals_to_float(message_dict)
        return message_dict

    @timeit
    def put(self, proto_obj: Message, check_for_changes: bool = True) -> str:

        item_id = getattr(proto_obj, self.primary_key)
        assert item_id != '', f'Protobuf Message of type {self.proto_class.__name__} has set primary key' \
                              f' {self.primary_key} as the empty string. This will cause collisions in ' \
                              f'the database and duplicate keys problems'

        if check_for_changes:
            old_proto = self.get(item_id)
            if old_proto == proto_obj:
                return item_id

        item_payload = self._encode_dict(proto_obj)

        self.__table.put_item(
            Item=item_payload,
        )
        return item_id

    @timeit
    def get(self, item_id: str, decode: bool = True) -> Message:

        response = self.__table.get_item(
            Key={
                self.primary_key: item_id,
            }
        )
        proto_dict = response.get('Item', None)
        if proto_dict is None:
            new_obj = self.proto_class()
            setattr(new_obj, self.primary_key, item_id)
            return new_obj

        if proto_dict.get("last_modified") is not None:
            del proto_dict['last_modified']

        proto_dict = self._decode_dict(proto_dict)

        if decode:
            return ParseDict(proto_dict, self.proto_class())
        else:
            return proto_dict

    @timeit
    def batch_put(self,
                  proto_obj_list: List[Message],
                  check_for_changes: bool = True) -> List[str]:
        # The max amount of operations that can be put in a Batch Writer is 25

        item_ids = [getattr(proto_obj, self.primary_key) for proto_obj in proto_obj_list]
        for item_id in item_ids:
            assert item_id != '', f'Protobuf Message of type {self.proto_class.__name__} has set primary key' \
                                  f' {self.primary_key} as the empty string. This will cause collisions in ' \
                                  f'the database and duplicate keys problems'
        old_protos = self.batch_get(item_ids)

        if len(proto_obj_list) > 25:
            out = []
            for sub_batch, old_batch in [(proto_obj_list[n:n+25], old_protos[n:n+25])
                                         for n in range(0, len(proto_obj_list), 25)]:
                out.extend(self.__batch_put(sub_batch, old_batch))
            return out
        else:
            return self.__batch_put(proto_obj_list, old_protos)

    def __batch_put(self,
                    proto_obj_list: List[Message],
                    old_protos: List[Message],
                    check_for_changes: bool = True,
                    ) -> List[str]:

        item_ids = [getattr(proto_obj, self.primary_key) for proto_obj in proto_obj_list]
        with self.__table.batch_writer() as writer:
            for item_id, proto_obj, old_proto in zip(item_ids, proto_obj_list, old_protos):
                if old_proto == proto_obj:
                    # Object to insert in database without any change, skipping
                    continue

                item_payload = self._encode_dict(proto_obj)

                writer.put_item(
                    Item=item_payload,
                )
        return item_ids

    @timeit
    def batch_get(self, item_ids: List[str], decode: bool = True) -> List[Message]:
        # We can retrieve at most 100 items at a time
        slicing_size = 100
        out_items = {}
        unprocessed_keys = []
        request_ids = []

        # noinspection PyTypeChecker
        for sub_batch in grouper(item_ids, slicing_size):
            # We need to save the request_ids here, so that we don't need to copy
            # the iterator and the access them only once
            request_ids.extend(sub_batch)
            items, remaining_keys = self.__batch_get(sub_batch, decode)
            out_items.update(items)
            unprocessed_keys.extend(remaining_keys)

        retries, max_retries = 0, 10
        while len(unprocessed_keys) > 0:
            # exponential backoff to request for the missing requested keys
            time.sleep(0.1 * 2**retries)
            retries += 1
            if retries > max_retries:
                raise Exception("Max retries exceeded, cannot fetch items. Is the table under-provisioned?")

            item_ids = unprocessed_keys
            unprocessed_keys = []
            for sub_batch in [item_ids[n:n+slicing_size] for n in range(0, len(item_ids), slicing_size)]:
                items, remaining_keys = self.__batch_get(sub_batch, decode)
                out_items.update(items)
                unprocessed_keys.extend(remaining_keys)

        assert unprocessed_keys == [], 'Unprocessed_keys are not all been fetched'

        # Formatting the output to match the list of ids that has been submitted
        out_list = []
        for item_id in request_ids:
            out_list.append(out_items.get(item_id))
        return out_list

    def __batch_get(self, item_ids: List[str], decode: bool = True) -> List[Message]:

        response = self.__client.batch_get_item(
            RequestItems={
                self.__table.name: {
                    'Keys': [
                        {
                            self.primary_key: {
                                'S': item_id
                            }
                        } for item_id in item_ids
                    ]
                }
            }
        )

        items_list = response['Responses'][self.__table.name]
        output_dict = {}
        for item in items_list:

            if item.get("last_modified") is not None:
                del item['last_modified']

            # Remove type information from the returned dictionary
            for key, value in item.items():
                item[key] = self.deserializer.deserialize(value)

            item = self._decode_dict(item)
            item_id = item[self.primary_key]
            if decode:
                output_dict[item_id] = ParseDict(item, self.proto_class())
            else:
                output_dict[item_id] = item

        unprocessed_keys = response['UnprocessedKeys'].get(self.__table.name)
        if unprocessed_keys is not None:
            unprocessed_keys = [item[self.primary_key]['S'] for item in unprocessed_keys['Keys']]
        else:
            unprocessed_keys = []

        return output_dict, unprocessed_keys

    @timeit
    def scan_ids(self, scan_filter=None) -> Iterator[str]:

        scan_kwargs: Dict[str, str] = {
            'ProjectionExpression': self.primary_key,
        }

        if scan_filter is not None:
            scan_kwargs['FilterExpression'] = scan_filter

        response = self.__table.scan(**scan_kwargs)
        for item_id in response['Items']:
            yield item_id.get(self.primary_key)

        while response.get('LastEvaluatedKey'):
            scan_kwargs['ExclusiveStartKey'] = response.get('LastEvaluatedKey')
            response = self.__table.scan(**scan_kwargs)
            for item_id in response['Items']:
                yield item_id.get(self.primary_key)
