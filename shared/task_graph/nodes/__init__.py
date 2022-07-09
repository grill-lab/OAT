from .abstract_node import AbstractNode, ProtoNode, StatementResolution

from .condition_node import ConditionNode
from .requirement_node import RequirementNode
from .execution_node import ExecutionNode
from .recommendation_node import RecommendationNode
from .action_node import ActionNode
from .extra_node import ExtraNode
from .logic_nodes import *
from .logic_nodes import builder as logic_builder

def builder(proto_node: ProtoNode) -> AbstractNode:

    if type(proto_node).__name__ == "ExecutionStep":
        node_class = ExecutionNode
    elif type(proto_node).__name__ == "Recommendation":
        node_class = RecommendationNode
    elif type(proto_node).__name__ == "Requirement":
        node_class = RequirementNode
    elif type(proto_node).__name__ == "Condition":
        node_class = ConditionNode
    elif type(proto_node).__name__ == "LogicNode":
        return logic_builder(proto_node)
    elif type(proto_node).__name__ == "Action":
        node_class = ActionNode
    elif type(proto_node).__name__ == "ExtraInfo":
        node_class = ExtraNode
    else:
        raise Exception("Node type not supported")

    return node_class.parse_proto(proto_node)
