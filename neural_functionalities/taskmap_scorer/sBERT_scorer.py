import torch
import torch.nn.functional as F

from .abstract_scorer import AbstractScorer
from searcher_pb2 import ScoreCandidateInput, ScoreCandidateOutput

from transformers import (
    AutoTokenizer, AutoModel
)

from utils import Downloader


class sBERTScorer(AbstractScorer):

    def __init__(self):
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"

        artefact_id = "sBERT"
        downloader = Downloader()
        downloader.download([artefact_id])
        sbert_path = downloader.get_artefact_path(artefact_id)

        self.model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2',
                                               cache_dir=sbert_path).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2',
                                                       cache_dir=sbert_path)
        self.model = self.model.eval()

    def score_candidate(self, score_candidate_input: ScoreCandidateInput) -> ScoreCandidateOutput:
        """ Use sBERT to score titles based on query, """
        query = str(score_candidate_input.query)
        titles = [str(title) for title in score_candidate_input.title]

        entries = [query] + titles

        encoded_input = self.tokenizer(entries, return_tensors='pt', padding=True)
        for k in encoded_input.keys():
            encoded_input[k] = encoded_input[k].to(self.device)
        with torch.no_grad():
            model_output = self.model(**encoded_input)

        sentence_embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        query_embedding = sentence_embeddings[0:1].repeat(len(titles), 1) # [num_docs, 512]
        doc_embeddings = sentence_embeddings[1:] # [num_docs, 512]

        cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
        scores = cos(query_embedding, doc_embeddings).tolist()

        score_candidate_output = ScoreCandidateOutput()
        score_candidate_output.score.extend(scores)

        return score_candidate_output

    @staticmethod
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]  # First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
