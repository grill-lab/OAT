import random
import sys
import os

sys.path.insert(0, '../../shared')
sys.path.insert(0, '../../shared/compiled_protobufs')
from searcher_pb2 import TaskMapList
from compiled_protobufs.taskmap_pb2 import OutputInteraction, ScreenInteraction, Image, Video
from google.protobuf.json_format import MessageToDict

from task_graph import *
import json


def process_graph(task_graph, steps):
    """ Update task_graph given steps, i.e. list of (text, image url) tuples representing each execution graph. """
    prev_node_id = None
    for step in steps:
        # Unpack step
        text, description, image, video = step

        response = OutputInteraction()
        response.speech_text = text
        response.description = description

        # Screen Interaction
        response.screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
        response.screen.headline = "Step %d out of %d"
        response.screen.paragraphs.append(text)

        # Add image if present.
        if len(image) > 0:
            screen_image: Image = response.screen.image_list.add()
            screen_image.path = image

        if video != "":
            step_video: Video = Video()
            step_video.hosted_mp4 = video["link"]
            step_video.start_time = video["start"]
            step_video.end_time = video["end"]

        node = ExecutionNode(
            response=response
        )
        current_node_id: str = task_graph.add_node(node)

        if prev_node_id is not None:
            task_graph.add_connection(prev_node_id, current_node_id)

        prev_node_id = current_node_id

    return task_graph


def build_taskgraph(doc):
    task_graph = TaskGraph()

    import hashlib
    md5 = hashlib.md5(doc["title"].encode('utf-8')).hexdigest()

    # attributes
    task_graph.set_attribute('dataset', 'theme_handcrafted')
    task_graph.set_attribute('taskmap_id', f'theme+handcrafted+{md5}')
    task_graph.set_attribute('title', str(doc['title']))
    task_graph.set_attribute('thumbnail_url', str(doc['image']))
    task_graph.set_attribute('domain_name', '')
    task_graph.set_attribute('description', str(doc['description']))
    task_graph.set_attribute('rating_out_100', int(round(random.uniform(4.5, 5.0), 1) * 20))
    task_graph.set_attribute('rating_count', random.randint(5, 25))
    task_graph.set_attribute('difficulty', "medium")

    # requirements
    for r in doc['requirementList']:
        node = RequirementNode(
            name=str(r),
            req_type='HARDWARE',
            amount='',
            linked_taskmap_id=''
        )
        task_graph.add_node(node)

    # steps
    steps = []
    for step in doc['steps']:
        text = str(step['text'])
        description = ''
        if step['image']:
            image = str(step['image'])
        else:
            image = str(doc['image'])

        if step.get('video', None) is not None:
            video = step['video']
        else:
            video = ""
        steps.append((text, description, image, video))

    return task_graph, steps

if __name__ == '__main__':
    hand_curated_path = '../../shared/file_system/offline/hand_curated/hand_crafted_fitness_v2.json'

    theme_recommendations_protos = {}
    with open(hand_curated_path, 'r') as f:
        dict_json = json.load(f)
        for theme in dict_json:

            taskmap_list = TaskMapList()

            for task in dict_json[theme]["candidates"]:
                task_graph, steps = build_taskgraph(task)
                task_graph = process_graph(task_graph, steps)
                # taskmap
                taskmap = task_graph.to_proto()
                # print(taskmap)
                taskmap_list.candidates.append(taskmap)

            theme_recommendations_protos[theme] = MessageToDict(taskmap_list)
            theme_recommendations_protos[theme]["description"] = dict_json[theme]["description"]
            theme_recommendations_protos[theme]["date"] = dict_json[theme].get("date", "")
            theme_recommendations_protos[theme]["intro_sentence"] = dict_json[theme].get("intro_sentence", "")
            theme_recommendations_protos[theme]["alternative_description"] = dict_json[theme].get("alternative_description", "")

    with open('curated_theme.json', 'w') as f:
        json.dump(theme_recommendations_protos, f, indent=4)
