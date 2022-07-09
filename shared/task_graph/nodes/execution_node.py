from .abstract_node import AbstractNode, StatementResolution
from taskmap_pb2 import ExecutionStep, OutputInteraction


class ExecutionNode(AbstractNode):

    def __init__(self,
                 *,
                 response: OutputInteraction = None,
                 active_duration: int = 1,
                 total_duration: int = 1,
                 **kwargs
                 ):
        super().__init__(**kwargs)

        self.response: OutputInteraction = response
        self.active_duration: int = active_duration
        self.total_duration: int = total_duration

    def resolution_status(self) -> StatementResolution:
        if len(self.parent_list) == 0:
            return self.status
        parents_res = [parent.resolution_status() for parent in self.parent_list]

        if any([res == StatementResolution.UNRESOLVED for res in parents_res]):
            return StatementResolution.UNRESOLVED
        if any([res == StatementResolution.FALSE for res in parents_res]):
            return StatementResolution.FALSE

        return self.status

    @property
    def proto_list(self) -> str:
        return "steps"

    def is_schedulable(self) -> bool:
        return True

    @staticmethod
    def parse_proto(proto: ExecutionStep) -> AbstractNode:
        return ExecutionNode(node_id=proto.unique_id,
                             response=proto.response,
                             active_duration=proto.active_duration_minutes,
                             total_duration=proto.total_duration_minutes,
                             )

    def to_proto(self) -> ExecutionStep:
        proto = ExecutionStep()

        proto.unique_id = self.node_id
        proto.response.ParseFromString(self.response.SerializeToString())
        proto.active_duration_minutes = self.active_duration
        proto.total_duration_minutes = self.total_duration
        return proto
