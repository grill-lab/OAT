import faiss
import torch
import torch.nn.functional as F
import pickle

import clip
import os
import json

from .abstract_image_searcher import AbstractImageSearcher
from image_searcher_pb2 import ImageRequest
from taskmap_pb2 import Image

from utils import get_file_system, logger

CACHE_PATH            = 'cache/neural_functionalities/ImageSearcher'
FAISS_INDEX_PATH      = 'indexes/image_index.faiss'
IMAGE_URL_LOOKUP_PATH = 'lookup_files/image_url_lookup.json'
IMAGE_LIST_PATH       = 'lookup_files/image_list.pkl'

class ImageSearcher(AbstractImageSearcher):

    def __init__(self) -> None:
        self.device = None
        self.model = None
        file_system = get_file_system()
        self.cache = os.path.join(file_system, CACHE_PATH)

        for path in [FAISS_INDEX_PATH, IMAGE_URL_LOOKUP_PATH, IMAGE_LIST_PATH]:
            if not os.path.exists(os.path.join(file_system, path)):
                logger.error(f'ImageSearcher: path {path} does not exist!')
                return

        self.image_index = faiss.read_index(os.path.join(file_system, FAISS_INDEX_PATH))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _  = clip.load("ViT-B/32", device=self.device, download_root=self.cache)
        
        self.url_lookup_dict = {}
        with open(os.path.join(file_system, IMAGE_URL_LOOKUP_PATH)) as url_lookup_file:
            lookup_data = json.load(url_lookup_file)
            for file_url_pair in lookup_data:
                self.url_lookup_dict.update(file_url_pair)
        
        with open(os.path.join(file_system, IMAGE_LIST_PATH), 'rb') as fp:
            self.all_images_list = pickle.load(fp)
    
    def search_image(self, image_request: ImageRequest) -> Image:
        if self.device is None or self.model is None:
            logger.warning('Image searching disabled! Data files missing?')
            return Image()

        logger.info(f"Searching for an image with {image_request.query}")
        with torch.no_grad():
            text = clip.tokenize([image_request.query]).to(self.device)
            text_features = self.model.encode_text(text)
            text_features = F.normalize(text_features, dim=-1)
        
        # might use the scores for thresholding later.. idk
        scores, indexes = self.image_index.search(
            text_features.cpu().numpy().astype('float32'), image_request.k
        )

        top_match_idx = indexes[0][0]
        top_match_score = scores[0][0]
        image_path = self.all_images_list[top_match_idx]

        image = Image()
        if top_match_score >= 0.3:
            image.path = self.url_lookup_dict[image_path]
            logger.info(f"Top Image Found: {image.path} <-> Score: {scores[0][0]}")

        return image
