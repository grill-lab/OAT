import boto3
from typing import Optional
from datetime import datetime
from botocore.exceptions import ClientError
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict, ParseDict


class ProtoDB:

    def __init__(self, proto_class, url=None):

        assert issubclass(proto_class, Message), "ProtoDB works only with protobuf classes"

        table_name = proto_class.__name__
        self.proto_class = proto_class

        dynamodb = boto3.resource('dynamodb', endpoint_url=url, region_name='us-east-1')

        try:
            self.__table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'dynamodb_id',
                        'KeyType': 'HASH'
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'dynamodb_id',
                        'AttributeType': 'S'
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
        except ClientError as e:
            self.__table = dynamodb.Table(table_name)

    def __format_item(self, obj: Message) -> dict:
        assert isinstance(obj,  self.proto_class), f"expecting object of type {self.proto_class}," \
                                                   f"but got {type(obj)}"

        payload = MessageToDict(obj)
        return payload

    def put(self, item_id: str, proto_obj: Message) -> None:

        item_payload = self.__format_item(proto_obj)
        item_payload['dynamodb_id'] = item_id
        item_payload['last_modified'] = datetime.now().isoformat()

        self.__table.put_item(
            Item=item_payload,
        )

    def get(self, item_id: str) -> Optional[Message]:

        response = self.__table.get_item(
            Key={
                'dynamodb_id': item_id,
            }
        )
        proto_dict = response.get('Item', None)
        if proto_dict is None:
            return self.proto_class()
        del proto_dict['dynamodb_id']

        if proto_dict.get("last_modified") is not None:
            del proto_dict['last_modified']

        return ParseDict(proto_dict, self.proto_class())
