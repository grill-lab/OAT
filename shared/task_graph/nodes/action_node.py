from .abstract_node import AbstractNode
from taskmap_pb2 import Action


class ActionNode(AbstractNode):

    def __init__(self,
                 *,
                 action_text: str,
                 **kwargs
                 ):
        super().__init__(**kwargs)

        self.action_text = action_text

    @property
    def proto_list(self):
        return "actions_list"

    def is_schedulable(self) -> bool:
        return False

    @staticmethod
    def parse_proto(proto: Action) -> AbstractNode:
        return ActionNode(node_id=proto.unique_id,
                          action_text=proto.action_text,
                          )

    def to_proto(self) -> Action:
        proto = Action()

        proto.unique_id = self.node_id
        proto.action_text = self.action_text
        return proto
