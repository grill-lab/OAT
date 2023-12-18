import torch

from .abstract_scorer import AbstractScorer
from searcher_pb2 import ScoreCandidateInput, ScoreCandidateOutput
from utils import logger

from transformers import (
    T5TokenizerFast, T5ForConditionalGeneration, T5Config
)


class T5Scorer(AbstractScorer):

    def __init__(self):
        logger.info("loading T5 tokenizer")
        config = T5Config.from_json_file("/shared/file_system/models/t5_scorer/config.json")
        self.model = T5ForConditionalGeneration(config)
        self.tokenizer = T5TokenizerFast.from_pretrained("t5-base")
        logger.info("loading T5 model")
        d = torch.load("/shared/file_system/models/t5_scorer/pytorch_model.bin")
        del d['decoder.block.0.layer.1.EncDecAttention.relative_attention_bias.weight']
        self.model.load_state_dict(d, strict=True)
        self.model = self.model.eval()
        logger.info("T5 is Loaded!!!")

    def score_candidate(self, score_candidate_input: ScoreCandidateInput) -> ScoreCandidateOutput:
        """ Use T5 to score titles based on query, """
        query = score_candidate_input.query
        titles = score_candidate_input.title

        samples = [f"Query: {query} Document: {doc} Relevant:" for doc in titles]
        tokenized_samples = self.tokenizer(samples, return_tensors='pt', padding=True)
        outputs = self.model(input_ids=tokenized_samples['input_ids'],
                             attention_mask=tokenized_samples['attention_mask'],
                             decoder_input_ids=torch.tensor([[0]] * len(titles))).logits.softmax(-1)[:, :, 1176].tolist()

        scores = [s[0] for s in outputs]
        max_score = max(scores)
        normalised_scores = [t / max_score for t in scores]

        logger.info(f"Query: {query}")
        for title, score, norm_score in zip(titles, scores, normalised_scores):
            logger.info(f"Title: {title},    score: {score},    norm_score: {norm_score}")

        score_candidate_output = ScoreCandidateOutput()
        score_candidate_output.score.extend(normalised_scores)
        return score_candidate_output
