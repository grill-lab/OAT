import openai
import torch
import os
import pandas as pd

from taskmap_pb2 import ScreenInteraction, TaskMap, ExtraInfo, ExecutionStep
from utils import logger, get_file_system, Downloader
from .abstract_step_augmenter import AbstractBatchStepAugmenter
from sentence_transformers import SentenceTransformer, util

openai.api_key = ''


class FactAugmenter(AbstractBatchStepAugmenter):

    def __init__(self):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder="/shared/file_system/cache/offline/models/1_Pooling",
                                         device=self.device).to(self.device)

        artefact_id = "facts_json"
        downloader = Downloader()
        downloader.download([artefact_id])
        self.facts_data = pd.read_json(downloader.get_artefact_path(artefact_id))
        self.facts = self.facts_data['fact']
        self.facts = [fact for fact in self.facts if fact != ""]
        self.fact_keywords = self.facts_data['keyword']
        self.fact_keywords = [word for word in self.fact_keywords if word != ""]

        self.fact_embeddings = self.model.encode(self.facts, convert_to_tensor=True, batch_size=128,
                                                 show_progress_bar=True)
        logger.info('Fact embeddings successfully encoded')

    def batch_process(self, batch):
        input_list = []
        output_list = []
        for (_, step, _) in batch:
            step_text = step.response.speech_text
            input_list.append(step_text)

        step_embeddings = self.model.encode(input_list, convert_to_tensor=True, batch_size=128, show_progress_bar=True)
        logger.info('Step embeddings successfully encoded')

        for step_idx, step_embedding in enumerate(step_embeddings):
            similarity_scores = util.cos_sim(step_embedding, self.fact_embeddings)[0]
            sorted_idxs = similarity_scores.argsort(descending=True)

            reranked_facts = [self.facts[i] for i in sorted_idxs]
            reranked_fact_keywords = [self.fact_keywords[i] for i in sorted_idxs]
            reranked_fact_scores = similarity_scores[sorted_idxs].tolist()

            most_relevant_fact = None
            most_relevant_score = 0

            for fact, fact_keyword, score in zip(reranked_facts, reranked_fact_keywords, reranked_fact_scores):
                if score > max(0.2, most_relevant_score) and fact_keyword in input_list[step_idx]:
                    most_relevant_fact = fact
                    most_relevant_score = score

            if most_relevant_score > 0:
                output_list.append([most_relevant_fact])
            else:
                output_list.append([])

        return output_list

    def condition(self, step: ExecutionStep) -> bool:
        return True

    def apply_output(self, step: ExecutionStep, processed_output) -> ExecutionStep:

        screen = ScreenInteraction()
        screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        for fact in processed_output:
            extra_info: ExtraInfo = ExtraInfo()
            extra_info.type = ExtraInfo.InfoType.FUNFACT
            extra_info.text = fact
            extra_info.keyword = self.facts_data[self.facts_data["fact"] == fact]['keyword'].iloc[0]
            image = self.facts_data[self.facts_data["fact"] == fact]['image'].iloc[0]
            if image != "":
                extra_info.image_url = image
            screen.extra_information.append(extra_info)
            logger.info(f"Matched fact '{fact}' with step '{step.response.speech_text}'")

        step.response.screen.MergeFrom(screen)

        return step

    def get_transformed_input(self, task_map: TaskMap):
        return None
