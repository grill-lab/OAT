from .abstract_node import AbstractNode
from taskmap_pb2 import Condition


class ConditionNode(AbstractNode):

    def __init__(self,
                 *,
                 condition_text: str,
                 default: str,
                 **kwargs
                 ):
        super().__init__(**kwargs)

        self.condition_text = condition_text
        self.default = default

    @property
    def proto_list(self):
        return "condition_list"

    def is_schedulable(self) -> bool:
        return False

    @staticmethod
    def parse_proto(proto: Condition) -> AbstractNode:
        return ConditionNode(node_id=proto.unique_id,
                             condition_text=proto.text,
                             default=proto.default
                             )

    def to_proto(self) -> Condition:
        proto = Condition()

        proto.unique_id = self.node_id
        proto.text = self.condition_text
        proto.default = self.default
        return proto
