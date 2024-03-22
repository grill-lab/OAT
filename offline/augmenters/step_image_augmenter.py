import faiss
import torch
import pickle
import clip
import os
import json
import random
import spacy

from taskmap_pb2 import Image, ScreenInteraction, TaskMap, Session, ExecutionStep
from .abstract_step_augmenter import AbstractBatchStepAugmenter
from utils import get_file_system, logger, Downloader

CACHE_PATH = 'cache/neural_functionalities/ImageSearcher'

nlp = spacy.load('en_core_web_sm')


class StepImageAugmenter(AbstractBatchStepAugmenter):

    def __init__(self) -> None:
        super().__init__()
        file_system = get_file_system()
        self.cache = os.path.join(file_system, CACHE_PATH)

        artefact_ids = ['faiss_index', 'image_url_lookup', 'image_list']
        downloader = Downloader()
        downloader.download(artefact_ids)
        for artefact_id in artefact_ids:
            path = downloader.get_artefact_path(artefact_id)
            if not os.path.exists(path):
                logger.error(f'ImageSearcher: path {path} does not exist!')
                exit(1)  # augmenter cannot run if the required model is not downloaded

        self.image_index = faiss.read_index(downloader.get_artefact_path('faiss_index'))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/32", device=self.device, download_root=self.cache)

        with open(downloader.get_artefact_path('image_url_lookup'), 'rb') as url_lookup_file:
            self.url_lookup_dict = json.load(url_lookup_file)

        with open(downloader.get_artefact_path('image_list'), 'rb') as fp:
            self.all_images_list = pickle.load(fp)
        
        logger.info("Loaded image augmentation models")

    def condition(self, step: ExecutionStep) -> bool:
        if len(step.response.screen.image_list) > 0:
            return False
        return True

    def get_transformed_input(self, taskmap: TaskMap) -> TaskMap:
        # -- Thumbnail --
        thumbnail_url = taskmap.thumbnail_url
        if taskmap.thumbnail_url == "":
            # make default
            default_cooking = [f'https://oat-2-data.s3.amazonaws.com/images/cooking-{i}.jpg' for i in
                               range(1, 17)]
            default_diy = [f'https://oat-2-data.s3.amazonaws.com/images/diy-{i}.jpg' for i in range(1, 8)]

            if taskmap.domain_name == Session.Domain.COOKING:
                thumbnail_url = random.choice(default_cooking)
            else:
                thumbnail_url = random.choice(default_diy)

        return thumbnail_url, taskmap.title

    def apply_output(self, step: ExecutionStep, image_url) -> ExecutionStep:
        logger.info(f'Step text: "{step.response.speech_text}" aligned to image: "{image_url}" ')
        screen: ScreenInteraction = ScreenInteraction()
        image: Image() = Image()
        image.path = image_url
        screen.image_list.append(image)
        step.response.screen.MergeFrom(screen)
        return step

    @staticmethod
    def get_step_text(step, task_title) -> str:
        words = nlp(step.response.screen.paragraphs[0])
        query = " ".join(word.text for word in words if (not word.is_stop and not word.is_punct))
        return f"a photo of {task_title}. {query[:50]}"

    def batch_process(self, batch):
        input_list = []
        default_images = []

        for (hash_val, step, (thumbnail_url, taskmap_title)) in batch:
            default_images.append(thumbnail_url)
            step_text = self.get_step_text(step, taskmap_title)
            input_list.append(step_text)

        try:
            tokenized_text = clip.tokenize(input_list).to(self.device)
        except:
            return []

        with torch.no_grad():
            text_features = self.model.encode_text(tokenized_text)

        scores, indexes = self.image_index.search(text_features.cpu().numpy().astype('float32'), k=1)
        image_urls = []

        for i in range(len(indexes)):
            top_match_idx = indexes[i][0]
            top_match_score = scores[i][0]
            if top_match_score > 3:
                image_path = self.all_images_list[top_match_idx]
                image_url = self.url_lookup_dict[image_path]
            else:
                image_url = default_images[i]

            image_urls.append(image_url)

        return image_urls
