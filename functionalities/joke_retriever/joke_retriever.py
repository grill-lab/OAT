import os
import json
import random

from taskmap_pb2 import ExtraInfo
from utils import get_file_system, logger, Downloader


class JokeRetriever:

    def __init__(self):
        artefact_id = "jokes_json"
        downloader = Downloader()
        downloader.download([artefact_id])
        joke_path = downloader.get_artefact_path(artefact_id)
        with open(joke_path) as f:
            self.jokes = json.load(f)

    def get_random_joke(self):
        extra_info: ExtraInfo = ExtraInfo()
        extra_info_json = random.choice(self.jokes)
        extra_info.keyword = extra_info_json.get('keyword')
        extra_info.text = extra_info_json.get('joke')
        extra_info.image_url = extra_info_json.get('image', "")
        extra_info.type = ExtraInfo.InfoType.JOKE
        logger.info(extra_info)
        return extra_info
