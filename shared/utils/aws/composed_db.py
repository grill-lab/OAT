from google.protobuf.message import Message
from google.protobuf.internal.containers import MessageMap, RepeatedCompositeFieldContainer

from .timeit import *
from .new_proto_db import ProtoDB, check_attr
from datetime import datetime
from google.protobuf.json_format import MessageToDict

try:
    from google.protobuf.pyext._message import RepeatedCompositeContainer
except:
    RepeatedCompositeContainer = RepeatedCompositeFieldContainer
    # This will happen in all non-pyext implementations of Protobuffers
    pass


class ComposedDB(ProtoDB):

    def __init__(self, proto_class, *,
                 url=None,
                 prefix: str = "Undefined",
                 primary_key: str = 'id',
                 sub_proto_config: list = None):
        """
            Initialization method for the Composed DB object, that aims to provide an easy interface between
            protobuf objects and a dynamodb Instance

            @param proto_class: Protobuf Message that will be saved by the ComposedDB. This will be the only accepted
                message that the database will save and load, providing automatic encoding and decoding
            @param url: Optional parameter to route the DynamoDB endpoint to a non-Cloud instance
            @param prefix: string to append in front of the table name. It can be used to route between different
                environment databases like Production and Development
            @param primary_key: string that represents the Message attribute to use as primary_key
            @param sub_proto_config: configuration that maps how to decompose the current object, is a dictionary of
                dictionaries composed like this:
                'message_param': {
                        'proto_class': SubMessageClass
                        'primary_key': 'sub_message_id'
                }

            @return None

        """
        assert issubclass(proto_class, Message), "ComposedDB works only with protobuf classes"
        self.proto_class = proto_class
        # self.primary_key = primary_key

        super().__init__(proto_class,
                         url=url,
                         prefix=prefix,
                         primary_key=primary_key)

        self.sub_tables = {}
        self.param_list = []
        self.config = sub_proto_config

        for param, config in sub_proto_config.items():
            proto_class = config['proto_class']
            primary_key = config['primary_key']

            # test that the param configured is part of the main protobuf object
            check_attr(self.proto_class, param)

            self.param_list.append(param)
            self.sub_tables[proto_class.__name__] = ProtoDB(proto_class,
                                                            primary_key=primary_key,
                                                            url=url,
                                                            prefix=prefix)

    def __put_sub(self, sub_message):

        if issubclass(type(sub_message), MessageMap):
            raise NotImplementedError()

        elif issubclass(type(sub_message), RepeatedCompositeFieldContainer) or \
                issubclass(type(sub_message), RepeatedCompositeContainer):
            if len(sub_message) > 0:
                table_name = sub_message[0].__class__.__name__
                output = self.sub_tables[table_name].batch_put(sub_message)
            else:
                output = []

        elif issubclass(type(sub_message), Message):
            output = self.sub_tables[sub_message.__class__.__name__].put(sub_message)
        else:
            # This should NEVER happen
            logger.error(f"Sub-message of type {type(sub_message)} cannot be decomposed in a separate table.")
            raise Exception("Trying to store a non-Protobuf Message")

        return output

    def __get_sub(self, item_ids, proto_name):

        table = self.sub_tables[proto_name]

        if type(item_ids) == dict:
            raise NotImplementedError()
        elif type(item_ids) == list:
            output = table.batch_get(item_ids, decode=False)
        elif type(item_ids) == str:
            output = table.get(item_ids, decode=False)
        else:
            raise Exception('Unexpected type for sub_field of object')

        return output

    def _encode_dict(self, obj: Message) -> dict:

        payload = super()._encode_dict(obj)

        for param in self.param_list:
            payload[param] = self.__put_sub(getattr(obj, param))
        return payload

    def _decode_dict(self, message_dict: dict) -> dict:
        for param, config in self.config.items():
            proto_name = config['proto_class'].__name__
            message_dict[param] = self.__get_sub(message_dict[param], proto_name)

        message_dict = super()._decode_dict(message_dict)
        return message_dict
