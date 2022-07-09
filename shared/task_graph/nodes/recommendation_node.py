from .abstract_node import AbstractNode
from taskmap_pb2 import Recommendation


class RecommendationNode(AbstractNode):

    def __init__(self,
                 *,
                 text: str,
                 rec_type: str,
                 **kwargs):
        super().__init__(**kwargs)

        self.recommendation_type = rec_type
        self.recommendation_text = text

    @property
    def proto_list(self) -> str:
        return "recommendation_list"

    def is_schedulable(self) -> bool:
        return False

    @staticmethod
    def parse_proto(proto: Recommendation) -> AbstractNode:
        # Conversion of type from Enum to String
        string_type = Recommendation.RecommendationType.Name(proto.type)

        return RecommendationNode(node_id=proto.unique_id,
                                  text=proto.type,
                                  rec_type=string_type
                                  )

    def to_proto(self) -> Recommendation:
        proto = Recommendation()

        proto.unique_id = self.node_id
        proto.text = self.recommendation_text
        proto.type = Recommendation.RecommendationType.Value(self.recommendation_type)
        return proto
