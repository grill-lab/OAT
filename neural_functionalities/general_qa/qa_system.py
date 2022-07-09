import torch

from typing import Dict, List
from .abstract_qa import AbstractQA

from taskmap_pb2 import Session
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList

from utils import logger
from task_graph import *

from transformers import set_seed, AutoTokenizer, AutoModelForSeq2SeqLM, pipeline


class NeuralGeneralQA(AbstractQA):

    def __init__(self) -> None:
        set_seed(42)
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "google/t5-small-ssm-nq"
        cache_dir = '/shared/file_system/models/general_question_answering'
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name, cache_dir=cache_dir
        ).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir=cache_dir
        )

        logger.info("Loaded General QA model")

    def rewrite_query(self, session: Session) -> QAQuery:
        # Query is the last turn utterance, top K not needed for this imp.
        response: QAQuery = QAQuery()
        response.text = session.turn[-1].user_request.interaction.text

        return response
    
    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        pass
    
    def synth_response(self, request: QARequest) -> QAResponse:
        
        response: QAResponse = QAResponse()
        query: str = request.query.text

        input_ids = self.tokenizer(query, return_tensors="pt").input_ids.to(self.device)
        generated_output = self.model.generate(input_ids).to(self.device)[0]

        response.text = self.tokenizer.decode(generated_output, skip_special_tokens=True)

        return response