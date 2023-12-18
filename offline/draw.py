# Set up jupyter notebook file environment

# ```python
# import sys
# sys.path.insert(0, '../shared/compiled_protobufs')
# from taskmap_pb2 import TaskMap
# from draw import read_protobuf_list_from_file # converts a .proto file into a taskmap
# from draw import get_task_visualization # shows a visualization of a taskmap
# ```

# Steps to set up the environment:

# 1. Create .ipynb file and download python extension in vscode
# 2. Run the following commands:

# ```
# sudo apt-get install python3.10-venv
# sudo apt install python3-pip
# python3 -m venv viewer-env
# source viewer-env/bin/activate 
# sudo apt-get install graphviz
# pip3 install -r requirements-task-viewer.py
# ```

# 3. Select viewer-env environment in the jupyter notebook file

# Examples of methods:
# task = read_protobuf_list_from_file(<filepath to the proto file>)
# get_task_visualization(task, jupyter_notebook=True, png_filename="")


from taskmap_pb2 import TaskMap
import os
import glob

from IPython.display import Image, display
from PIL import Image as Im
import pydot


def parse_taskgraph(taskmap: TaskMap):
    parsed_info = {}
    parsed_info["title"] = taskmap.title
    parsed_info["dataset"] = taskmap.dataset
    parsed_info["thumbnail"] = taskmap.thumbnail_url
    parsed_info["steps"] = taskmap.steps
    parsed_info["conditions"] = taskmap.condition_list
    parsed_info["conditions_dict"] = {condition.unique_id: condition.text for condition in taskmap.condition_list}

    # requirements in the form (id, name+amount)

    parsed_info["requirements_step_links"] = get_links_step_ingredients(taskmap.connection_list,
                                                                        parsed_info["requirements_dict"].keys())
    parsed_info["step_links"] = get_step_links(taskmap.connection_list, taskmap.steps)
    parsed_info["all_links"] = get_all_links(taskmap.connection_list)
    parsed_info["logic_nodes_ids"] = {node.unique_id: node.type for node in taskmap.logic_nodes_list}
    parsed_info["action_nodes_ids"] = {node.unique_id for node in taskmap.actions_list}
    parsed_info["visited_nodes"] = set()

    task_info = {}
    if taskmap.rating_count:
        task_info["rating count"] = taskmap.rating_count
    if taskmap.domain_name:
        task_info["domain"] = taskmap.domain_name
    if taskmap.author:
        task_info["author"] = taskmap.author
    if taskmap.difficulty:
        task_info["difficulty"] = taskmap.difficulty
    if taskmap.views:
        task_info["views"] = taskmap.view
    if taskmap.date:
        task_info["date"] = taskmap.date

    parsed_info["task_info"] = task_info

    return parsed_info


def get_first_taskgraph_step(connections, steps):
    """Connection list contains links to both ingredients and next steps."""
    step_ids = {step.unique_id for step in steps}
    # Filter out step ids 
    nodes_from = {connection.id_from for connection in connections}.intersection(step_ids)
    nodes_to = {connection.id_to for connection in connections}.intersection(step_ids)
    starting_nodes = nodes_from.difference(nodes_to)
    if len(starting_nodes) != 1:
        raise Exception(f"Cannot determine staring node of the taskgraph. Found {len(starting_nodes)} starting nodes.")
    return starting_nodes.pop()


def get_links_step_ingredients(connections, requirement_ids):
    ingredient_nodes = {connection.id_from for connection in connections}.intersection(requirement_ids)
    check_ingredient_link = lambda connection: connection.id_from in ingredient_nodes
    links = list(filter(check_ingredient_link, connections))

    links_dict = {}  # key: id of a step, val: list[] of ids to ingredients
    for link in links:
        if link.id_to in links_dict:
            links_dict[link.id_to].append(link.id_from)
        else:
            links_dict[link.id_to] = [link.id_from]

    return links_dict


def get_step_links(connections, steps):
    step_ids = {step.unique_id for step in steps}

    step_nodes = {connection.id_from for connection in connections}.intersection(step_ids)
    check_step_link = lambda connection: connection.id_from in step_nodes
    links = list(filter(check_step_link, connections))

    links_dict = {}  # key: id of a step, val: list[] of ids to ingredients
    for link in links:
        if link.id_from in links_dict:
            links_dict[link.id_from].append(link.id_to)
        else:
            links_dict[link.id_from] = [link.id_to]

    return links_dict


def get_all_links(connections):
    links_dict = {}  # key: id of a node, val: list[] of ids to next node
    for link in connections:
        if link.id_from in links_dict:
            links_dict[link.id_from].append(link.id_to)
        else:
            links_dict[link.id_from] = [link.id_to]

    return links_dict


def read_protobuf_list_from_file(path, proto_message):
    taskmap = proto_message()
    f = open(path, "rb")
    taskmap.ParseFromString(f.read())
    f.close()
    return taskmap


def view_pydot(pdot):
    plt = Image(pdot.create_png())
    display(plt)


def scale_img_by_width(filename):
    base_width = 150
    img = Im.open(filename)
    w_percent = (base_width / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, hsize), Im.ANTIALIAS)
    img.save(filename)


def download_image(url, filename):
    import requests
    try:
        img_data = requests.get(url).content
        with open(filename, 'wb') as handler:
            handler.write(img_data)
        scale_img_by_width(filename)
        return True
    except IOError:
        return False


def delete_downloaded_images():
    # Getting All Files List
    file_list = glob.glob('image-*.jpg', recursive=False)

    # Remove all files one by one
    for file in file_list:
        try:
            os.remove(file)
        except OSError:
            print("Error while deleting file")


def delete_image(filename):
    try:
        os.remove(filename)
    except OSError:
        print("Error while deleting file")


def get_task_visualization(taskgraph, jupyter_notebook=True, png_filename=""):
    parsed_taskgraph = parse_taskgraph(taskgraph)

    graph = pydot.Dot(parsed_taskgraph["title"], graph_type='digraph', format="jpg", strict=True)

    prev_nodes = []
    node = add_heading(graph, parsed_taskgraph)
    prev_nodes.append(node)
    node = add_thumbnail(graph, parsed_taskgraph)
    prev_nodes.append(node)

    step_id = parsed_taskgraph["first_step_id"]

    prev_nodes2 = []

    if parsed_taskgraph["task_info"] != {}:
        node = add_task_info(graph, parsed_taskgraph, prev_nodes)
        prev_nodes2 = [node]

    node = add_requirements(graph, parsed_taskgraph, prev_nodes)
    prev_nodes2 += [node]
    node = add_extra_info(graph, parsed_taskgraph, prev_nodes)

    add_step(graph, step_id, parsed_taskgraph, prev_nodes2)

    if jupyter_notebook:
        view_pydot(graph)
    if len(png_filename) > 0:
        graph.write_png(png_filename + '.png')
    delete_downloaded_images()


def add_heading(graph, parsed_taskgraph):
    title = parsed_taskgraph["title"]
    dataset = parsed_taskgraph["dataset"]
    heading = f"{title} by {dataset}"

    heading_node = pydot.Node("title", label=heading)
    heading_node.set_fontsize(14)
    heading_node.set_shape("plaintext")
    graph.add_node(heading_node)

    return {
        "id": "title",
        "show_edge": False
    }


def add_thumbnail(graph, parsed_taskgraph):
    img_name = "image-thumbnail.jpg"
    download_image(parsed_taskgraph["thumbnail"], img_name)

    imgNode = pydot.Node("thumbnail", label="", )
    imgNode.set_image(os.path.join(os.getcwd(), img_name))
    imgNode.set_shape("plaintext")
    graph.add_node(imgNode)

    return {
        "id": "thumbnail",
        "show_edge": False
    }


def add_requirements(graph, parsed_taskgraph, prev_nodes):
    requirements = parsed_taskgraph["requirements_dict"].values()
    requirements_text = []
    if len(requirements) > 0:
        requirements_text.append("Requirements:")
    for idx, requirement in enumerate(requirements):
        requirements_text.append(f"{idx + 1}. {requirement}")
    requirements_text = "\l".join(requirements_text)

    requirement_node = pydot.Node("requirements", label=f"{requirements_text}\l")
    requirement_node.set_fontsize(10)
    requirement_node.set_shape("note")
    graph.add_node(requirement_node)

    add_prev_edges(graph, "requirements", prev_nodes)

    return {
        "id": "requirements",
        "show_edge": False
    }


def add_task_info(graph, parsed_taskgraph, prev_nodes):
    task_info = parsed_taskgraph["task_info"]
    task_description = "Task info: \n"
    task_description += "\n".join([f"{info_descr}: {info_val}" for info_descr, info_val in task_info.items()])
    print(task_description)

    task_node = pydot.Node("task-info", label=f"{task_description}\l")
    task_node.set_fontsize(10)
    task_node.set_shape("note")
    graph.add_node(task_node)

    add_prev_edges(graph, "task-info", prev_nodes)

    return {
        "id": "task-info",
        "show_edge": False
    }


def add_extra_info(graph, parsed_taskgraph, prev_nodes):
    if len(parsed_taskgraph["extra_info_list"]) == 0:
        return

    extra_info = ["Requirements:"]
    for idx, info in enumerate(parsed_taskgraph["extra_info_list"]):
        extra_info.append(f"{idx + 1}. {info}")
    extra_info = "\l".join(extra_info)

    add_prev_edges(graph, "extra-info", prev_nodes)

    return {
        "id": "requirements",
        "extra-info": False
    }


def add_step(graph, step_id, parsed_taskgraph, prev_nodes):
    # print("step id", step_id)

    steps = [step for step in parsed_taskgraph["steps"] if step.unique_id == step_id]
    # print("all steps",parsed_taskgraph["steps"])
    # print(len(steps))
    # print("steps", [step.unique_id for step in steps])

    if step_id in parsed_taskgraph["conditions_dict"]:
        if " timer " in parsed_taskgraph["conditions_dict"][step_id]:
            return
    # if step_id == "05a0e671-1b98-4099-a61f-420c81fa32a5":
    #     print(step_id)
    #     print(parsed_taskgraph["action_nodes_ids"])

    # print(step_id)

    if len(steps) == 0:
        if step_id in parsed_taskgraph["logic_nodes_ids"] and parsed_taskgraph["logic_nodes_ids"][step_id] == "AnyNode":
            nextStep = parsed_taskgraph["all_links"][step_id][0]
            add_step(graph, nextStep, parsed_taskgraph, prev_nodes)
            return

    step = steps[0]

    ingredients = []
    # print("step", step_id)
    if step_id in parsed_taskgraph["requirements_step_links"]:
        ingredient_ids = parsed_taskgraph["requirements_step_links"][step_id]
        # print("ingredient_ids")
        # print(ingredient_ids)
        for ingredient_id in ingredient_ids:
            ingredients.append(parsed_taskgraph["requirements_dict"][ingredient_id])

    text_count = 0
    text_label = ""
    if len(step.response.description) > 0:
        text_label += shorten_text("description: " + step.response.description)
        text_count += 1
    if text_count > 0:
        text_label += '\n'
    if len(step.response.speech_text) > 0:
        text_label += shorten_text("speech_text: " + step.response.speech_text)
        text_count += 1
    if text_count > 0:
        text_label += '\n'
    if len(step.response.screen.video.title) > 0:
        text_label += shorten_text(
            "video: " + step.response.screen.video.title + "mp4_link: " + step.response.screen.video.hosted_mp4)
        text_count += 1
    if text_count > 0:
        text_label += '\n'
    if len(ingredients) > 0:
        text_label += "Linked ingredients: \n" + '\n'.join(ingredients)
    if len(step.response.screen.extra_information) > 0:
        extra_info = []
        for extra in step.response.screen.extra_information:
            extra_info.append(extra.text)
        text_label += "Linked extra info: \n" + '\n'.join(extra_info)

    pydot_node = pydot.Node(step_id, label=text_label)
    pydot_node.set_fontsize(14)
    graph.add_node(pydot_node)
    add_prev_edges(graph, step_id, prev_nodes)

    prev_n = []
    prev_n.append({
        "id": step_id,
        "show_edge": True
    })

    images = step.response.screen.image_list
    if images:
        # print(images[0])
        image_url = images[0].path
        img_name = f"image-{step_id}"
        is_downloadable = download_image(image_url, img_name + ".jpg")
        if is_downloadable:
            imgNode = pydot.Node(img_name, label="", )
            imgNode.set_image(os.path.join(os.getcwd(), img_name + ".jpg"))
            imgNode.set_shape("plaintext")
            graph.add_node(imgNode)

            for prev_node in prev_nodes:
                prev_node["show_edge"] = False

            add_prev_edges(graph, img_name, prev_nodes)

            prev_n.append({
                "id": img_name,
                "show_edge": False
            })

    next_nodes_dict = parsed_taskgraph["step_links"]

    if step_id in next_nodes_dict:
        next_node = next_nodes_dict[step_id]
        # find condition nodes
        conditions_step_ids = {condition.unique_id for condition in parsed_taskgraph["conditions"]}
        # print(conditions_step_ids)
        # print(step_id)
        # print(next_node)
        # check if condition comes next

        if len(next_node) == 0:
            return
        if len(next_node) == 1 and next_node[0] in conditions_step_ids:
            add_condtion(graph, next_node[0], parsed_taskgraph, prev_n)
            # find future nodes
        else:
            # print("FOUND NODES")
            next_steps = next_nodes_dict[step_id]
            for step_id in next_steps:
                add_step(graph, step_id, parsed_taskgraph, prev_n)


def add_condtion(graph, condition_id, parsed_taskgraph, prev_nodes):
    # print("ADD condition")
    condition = [condition for condition in parsed_taskgraph["conditions"] if condition_id == condition.unique_id][0]

    pydot_node = pydot.Node(condition_id, label=shorten_text(condition.text, breakpoint=5))
    pydot_node.set_fontsize(14)
    pydot_node.set_shape("diamond")
    graph.add_node(pydot_node)

    add_prev_edges(graph, condition_id, prev_nodes)

    next_id_1, next_id_2 = parsed_taskgraph["all_links"][condition_id]

    if next_id_1 in parsed_taskgraph["logic_nodes_ids"] and parsed_taskgraph["logic_nodes_ids"][next_id_1] == "NotNode":
        notNode, yesNode = next_id_1, next_id_2
    else:
        yesNode, notNode = next_id_1, next_id_2

    yesNode = parsed_taskgraph["all_links"][yesNode][0]
    notNode = parsed_taskgraph["all_links"][notNode][0]

    prev_n = []
    prev_n.append({
        "id": condition_id,
        "show_edge": True,
        "label": "YES"
    })

    add_step(graph, yesNode, parsed_taskgraph, prev_n)

    prev_n = []
    prev_n.append({
        "id": condition_id,
        "show_edge": True,
        "label": "No"
    })
    add_step(graph, notNode, parsed_taskgraph, prev_n)


def shorten_text(step_text, breakpoint=10):
    words = step_text.split(" ")
    shortened_text = "\n".join([' '.join(words[i:i + breakpoint]) for i in range(0, len(words), breakpoint)])
    return shortened_text


def add_prev_edges(graph, id, prev_nodes):
    for node in prev_nodes:
        if node["show_edge"]:
            if "label" in node:
                edge = pydot.Edge(node["id"], id, label=node["label"], fontsize="14")
            else:
                edge = pydot.Edge(node["id"], id)
        else:
            edge = pydot.Edge(node["id"], id, color="white")
            # edge = pydot.Edge(node["id"], id)
        graph.add_edge(edge)
