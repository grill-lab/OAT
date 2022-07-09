from .abstract_node import AbstractNode, StatementResolution
from taskmap_pb2 import Requirement
from typing import Mapping

class RequirementNode(AbstractNode):

    def __init__(self,
                 *,
                 name: str,
                 req_type: str,
                 amount: str = "",
                 linked_taskmap_id: str = "",
                 **kwargs):
        super().__init__(**kwargs)

        self.name: str = name
        self.requirement_type: str = req_type
        self.amount = amount
        self.linked_taskmap_id = linked_taskmap_id

    def resolution_status(self):
        return StatementResolution.TRUE

    @property
    def proto_list(self) -> str:
        return "requirement_list"

    def is_schedulable(self) -> bool:
        return False

    @staticmethod
    def parse_proto(proto: Requirement) -> AbstractNode:
        string_type = Requirement.RequirementType.Name(proto.type)

        return RequirementNode(node_id=proto.unique_id,
                               name=proto.name,
                               amount=proto.amount,
                               linked_taskmap_id=proto.linked_taskmap_id,
                               req_type=string_type
                               )

    def to_proto(self) -> Requirement:
        proto = Requirement()

        proto.unique_id = self.node_id
        proto.name = self.name
        proto.amount = self.amount
        proto.linked_taskmap_id = self.linked_taskmap_id
        proto.type = Requirement.RequirementType.Value(self.requirement_type)
        return proto

