
from .abstract_scorer import AbstractScorer
from searcher_pb2 import ScoreTaskMapInput, ScoreTaskMapOutput

from transformers import (AutoTokenizer, AutoModel, T5ForConditionalGeneration, T5Config)
import torch
from utils import logger, timeit
import torch.nn.functional as F
import time



class sBERTScorer(AbstractScorer):

    def __init__(self):
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("loading sBERT model")
        self.model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2', cache_dir='/shared/file_system/models/sBERT').to(self.device)
        logger.info("loading sBERT tokenizer")
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2', cache_dir='/shared/file_system/models/sBERT')
        self.model = self.model.eval()
        logger.info("sBERT is Loaded!!!")

    @timeit
    def score_taskmap(self, score_taskmap_input: ScoreTaskMapInput) -> ScoreTaskMapOutput:
        """ Use T5 to score titles based on query, """
        query = str(score_taskmap_input.query)
        titles = [str(title) for title in score_taskmap_input.title]

        entries = [query] + titles

        encoded_input = self.tokenizer(entries, return_tensors='pt', padding=True)
        for k in encoded_input.keys():
            encoded_input[k] = encoded_input[k].to(self.device)
        # print(tokenized_samples)
        with torch.no_grad():
            model_output = self.model(**encoded_input)

        sentence_embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        query_embedding = sentence_embeddings[0:1].repeat(len(titles), 1) # [num_docs, 512]
        doc_embeddings = sentence_embeddings[1:] # [num_docs, 512]

        cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
        scores = cos(query_embedding, doc_embeddings).tolist()

        score_taskmap_output = ScoreTaskMapOutput()
        score_taskmap_output.score.extend(scores)

        return score_taskmap_output

    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]  # First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)