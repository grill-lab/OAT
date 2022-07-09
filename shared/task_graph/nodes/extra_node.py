from .abstract_node import AbstractNode
from taskmap_pb2 import ExtraInfo


class ExtraNode(AbstractNode):

    def __init__(self,
                 *,
                 extra_type: str,
                 text: str,
                 **kwargs):
        super().__init__(**kwargs)

        self.extra_type: str = extra_type
        self.text: str = text

    @property
    def proto_list(self) -> str:
        return "extra_information"

    def is_schedulable(self) -> bool:
        return False

    @staticmethod
    def parse_proto(proto: ExtraInfo) -> AbstractNode:
        string_type = ExtraInfo.InfoType.Name(proto.type)

        return ExtraNode(node_id=proto.unique_id,
                         extra_type=string_type,
                         text=proto.text
                         )

    def to_proto(self) -> ExtraInfo:
        proto = ExtraInfo()

        proto.unique_id = self.node_id
        proto.text = self.text
        proto.type = ExtraInfo.InfoType.Value(self.extra_type)
        return proto
