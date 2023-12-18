import openai
import torch
import os
import pandas as pd

from taskmap_pb2 import ScreenInteraction, TaskMap, ExtraInfo, ExecutionStep
from utils import logger, get_file_system, Downloader
from .abstract_step_augmenter import AbstractBatchStepAugmenter
from sentence_transformers import SentenceTransformer, util

openai.api_key = ''


class JokeAugmenter(AbstractBatchStepAugmenter):

    def __init__(self):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder="/shared/file_system/cache/offline/models/1_Pooling",
                                         device=self.device).to(self.device)

        artefact_id = "jokes_json"
        downloader = Downloader()
        downloader.download([artefact_id])
        self.jokes_data = pd.read_json(downloader.get_artefact_path(artefact_id))
        self.jokes = self.jokes_data['joke']
        self.jokes = [joke for joke in self.jokes if joke != ""]
        self.joke_keywords = self.jokes_data['keyword']
        self.joke_keywords = [word for word in self.joke_keywords if word != ""]

        self.joke_embeddings = self.model.encode(self.jokes, convert_to_tensor=True,
                                                 batch_size=128, show_progress_bar=True)
        logger.info('Joke embeddings successfully encoded')

    def batch_process(self, batch):
        input_list = []
        output_list = []
        for (_, step, _) in batch:
            step_text = step.response.speech_text
            input_list.append(step_text)

        step_embeddings = self.model.encode(input_list, convert_to_tensor=True,
                                            batch_size=128, show_progress_bar=True)
        logger.info('Step embeddings successfully encoded')

        for step_idx, step in enumerate(zip(input_list, step_embeddings)):
            step_text, step_embedding = step
            similarity_scores = util.cos_sim(step_embedding, self.joke_embeddings)[0]
            sorted_idxs = similarity_scores.argsort(descending=True)

            reranked_jokes = [self.jokes[i] for i in sorted_idxs]
            reranked_joke_keywords = [self.joke_keywords[i] for i in sorted_idxs]
            reranked_joke_scores = similarity_scores[sorted_idxs].tolist()

            most_relevant_joke = None
            most_relevant_score = 0

            for joke, keyword, score in zip(reranked_jokes, reranked_joke_keywords, reranked_joke_scores):
                if score > max(0.2, most_relevant_score) and keyword in input_list[step_idx]:
                    most_relevant_joke = joke
                    most_relevant_score = score

            if most_relevant_score > 0:
                output_list.append([most_relevant_joke])
            else:
                output_list.append([])

        return output_list

    def condition(self, step: ExecutionStep) -> bool:
        potential_keywords = step.response.speech_text.strip().lower().split(" ")
        matched_keywords = self.jokes_data[self.jokes_data['keyword'].isin(potential_keywords)]['keyword'].tolist()
        return len(matched_keywords) > 0

    def apply_output(self, step: ExecutionStep, processed_output) -> ExecutionStep:

        screen = ScreenInteraction()
        screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        for joke in processed_output:
            extra_info = ExtraInfo(
                type='JOKE',
                text=joke,
                keyword=self.jokes_data[self.jokes_data["joke"] == joke]['keyword'].iloc[0]
            )
            image = self.jokes_data[self.jokes_data["joke"] == joke]['image'].iloc[0]
            if image != "":
                extra_info.image_url = image
            screen.extra_information.append(extra_info)
            logger.info(f"Matched joke '{joke}' with step '{step.response.speech_text}'")

        step.response.screen.MergeFrom(screen)

        return step

    def get_transformed_input(self, task_map: TaskMap):
        return None

    # def generate_jokes_from_step(self, step_text):
    #     prompt = f"""Tell me a clean joke that is related to {step_text} and is appropriate for children"""
    #
    #     response = openai.Completion.create(
    #         engine="text-davinci-002",
    #         prompt=prompt,
    #         max_tokens=50,
    #         top_p=1,
    #         frequency_penalty=0.2,
    #         presence_penalty=0.5,
    #         temperature=0.5
    #     )
    #     generator = JokeGenerator()
    #     generator.add_joke(response.choices[0].text)
    #     joke = response.choices[0].text
    #
    #     # with open(os.path.join(get_file_system(), 'offline/extra_info_data/jokes.txt'), 'a') as file:
    #     #    file.append(joke + '\n')
    #
    #     # logger.info("GENERATING JOKE" + kw + str(response.choices[0].text))
    #
    #     return joke
