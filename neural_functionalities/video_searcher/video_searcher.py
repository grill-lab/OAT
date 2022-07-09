import re
from .abstract_video_searcher import AbstractVideoSearcher
from video_searcher_pb2 import VideoQuery
from taskmap_pb2 import Session
from video_document_pb2 import VideoDocument

from sentence_transformers import SentenceTransformer, util
import json
from google.protobuf.json_format import Parse
from utils import get_file_system, logger
import os

class VideoSearcher(AbstractVideoSearcher):

    def __init__(self) -> None:
        self.embedder = SentenceTransformer(
            'all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling"
        )
        with open("video_searcher/videos_metadata.json") as videos_metadata_file:
            self.videos_metadata = json.load(videos_metadata_file)
            for video in self.videos_metadata:
                video['doc_id'] = video['id']
                del video['id']
        video_title_list = [video['title'] for video in self.videos_metadata]
        logger.info("computing video embeddings")
        self.video_list_embeddings = self.embedder.encode(video_title_list, convert_to_tensor=True)
        
    
    def search_video(self, query: VideoQuery) -> VideoDocument:

        logger.info(f"Searching for a video with {query.text}")
        query_embedding = self.embedder.encode(query.text, convert_to_tensor=True)
        recommended_video = VideoDocument()

        similarity_scores = util.cos_sim(query_embedding, self.video_list_embeddings)[0]
        sorted_idxs = similarity_scores.argsort(descending=True)

        reranked_videos = [self.videos_metadata[i] for i in sorted_idxs]
        # get scores
        reranked_video_scores = similarity_scores[sorted_idxs].tolist()

        # logging
        for index, (video, score) in enumerate(zip(reranked_videos, reranked_video_scores)):
            if score > 0.7:
                logger.info(f"RELEVANT VIDEO: {video['title']} {score}")
            elif score < 0.7 and score > 0.4:
                logger.info(f"IRRELEVANT VIDEO: {video['title']} {score}")
        
        if reranked_video_scores[0] > 0.7:
            recommended_video = Parse(
                json.dumps(reranked_videos[0]), VideoDocument()
            )
        else:
            logger.info("ALL Videos are below the threshold of 0.7")

        return recommended_video

