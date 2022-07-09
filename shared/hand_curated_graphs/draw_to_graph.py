import json
import re
import os
import uuid

from task_graph import TaskGraph
from taskmap_pb2 import OutputInteraction
from parsers import *


json_string = input("Insert the Json string: ")
json_string = re.sub("\n", r"\\n", json_string)

data = json.loads(json_string)
types = set()

nodes = {}
links = []

for el in data['elements']:
    if el['type'] == 'arrow':
        from_id = el['startBinding']['elementId']
        to_id = el['endBinding']['elementId']
        links.append((from_id, to_id))
    else:

        assert len(el.get('groupIds')) < 2, "Too many groups for block"
        # Take as Id the GroupId if available, or the container Id
        el_id = (el.get('groupIds') or [el.get('id')])[0]
        nodes[el_id] = nodes.get(el_id, [])
        nodes[el_id].append(el)

requirement_color = "#82c91e"
step_color = "#fab005"
condition_color = "#15aabf"
logic_color = "#868e96"
action_color = "#fa5252"

attributes_color = "#7950f2"
extra_color = "#40c057"

property_color = "#ced4da"

def get_group_color(obj_list):
    colors = set([])

    for obj in obj_list:
        if obj['type'] != "text":
            colors.add(obj['backgroundColor'])

    if property_color in colors:
        colors.remove(property_color)

    assert len(colors) == 1, "Group with conflicting coloring of elements"

    return colors.pop()

def get_group_id(obj_list):
    ids = set()

    for obj in obj_list:
        if obj['backgroundColor'] != property_color and obj["type"] != "text":
            ids.add(obj["id"])

    assert len(ids) == 1, "Leading Element not found in Group"
    return ids.pop()


translation_ids = {}
graph = TaskGraph()

for list_id, obj_list in nodes.items():

    group_color = get_group_color(obj_list)

    if group_color == requirement_color:
        node = RequirementParser().parse(obj_list)
    elif group_color == step_color:
        response = OutputInteraction()
        node = StepParser().parse(obj_list)
    elif group_color == condition_color:
        node = ConditionParser().parse(obj_list)
    elif group_color == logic_color:
        node = LogicParser().parse(obj_list)
    elif group_color == action_color:
        node = ActionParser().parse(obj_list)
    elif group_color == attributes_color:
        AttributesParser(graph).parse(obj_list)
        node = None
    elif group_color == extra_color:
        ExtraParser(graph).parse(obj_list)
        node = None
    else:
        print("WARNING: Color for node not supported!!")
        continue

    if node is not None:
        n_id = graph.add_node(node)
        translation_ids[get_group_id(obj_list)] = n_id

for from_id, to_id in links:
    graph.add_connection(translation_ids[from_id], translation_ids[to_id])


def uniquify(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + " (" + str(counter) + ")" + extension
        counter += 1

    return path


file_path = uniquify("out_dir/graph.proto")
with open(file_path, "wb+") as f:
    f.write(graph.to_proto().SerializeToString())

print(f"TaskMap has been written to {file_path}")
