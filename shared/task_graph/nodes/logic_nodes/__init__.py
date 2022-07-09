import sys
from .not_node import NotNode
from .any_node import AnyNode
from .wait_node import WaitNode
from .abstract_logic_node import AbstractLogicNode, AbstractNode

from taskmap_pb2 import LogicNode

def builder(proto: LogicNode) -> AbstractNode:

    node_class = getattr(sys.modules[__name__], proto.type)
    return node_class.parse_proto(proto)
