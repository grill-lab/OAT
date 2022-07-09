import torch

from typing import Dict, List
from .abstract_qa import AbstractQA

from taskmap_pb2 import Session
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList

from utils import logger
from task_graph import *

# from transformers import set_seed, AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from transformers import set_seed, AutoModelForQuestionAnswering, AutoTokenizer, pipeline
from .numbers import NumberSanitizer



class NeuralIntraTaskMapContextualQA(AbstractQA):

    def __init__(self) -> None:
        set_seed(42)

        device: str = -1 if not torch.cuda.is_available() else 0
        qa_model_name = "deepset/roberta-base-squad2"
        sa_model_name = "cardiffnlp/twitter-roberta-base-sentiment"

        qa_model_path = '/shared/file_system/models/task_question_answering'
        sa_model_path = '/shared/file_system/models/sentiment_analysis'

        self.qa_model = pipeline(
            'question-answering', 
            model=qa_model_name, 
            tokenizer=qa_model_name,
            model_kwargs = {"cache_dir": qa_model_path},
            device = device
        )
        logger.info("Loaded Task QA model")

        self.sentiment_classifier = pipeline('sentiment-analysis', 
                            model=sa_model_name, 
                            model_kwargs = {"cache_dir": sa_model_path}, 
                            device = device)
        logger.info("Loaded Sentiment Analysis model")

        self.sanitizer = NumberSanitizer()
    
    def __get_sentiment_classification(self, question: str) -> List[Dict]:
        """
        Run sentiment analysis on the User's query to assess how dangerous it is
        """

        with torch.no_grad():
            return self.sentiment_classifier(question)
    
    
    def __build_context(self, task_graph: TaskGraph) -> str:
        """
        Creates the optimal context given to the model for inference
        """

        requirements: str = 'These are the requirements\n'
        steps: str = 'These are the steps\n'

        for key, value in task_graph.node_set.items():
            
            if value.__class__.__name__ == "RequirementNode":
                requirements += self.sanitizer(value.name) + '\n'
            if value.__class__.__name__ == "ExecutionNode":
                steps += self.sanitizer(value.response.speech_text) + '\n'
        
        return "{}\n{}".format(requirements, steps)



    def rewrite_query(self, session: Session) -> QAQuery:
        # Query is the last turn utterance, top K not needed for this imp.
        response: QAQuery = QAQuery()
        response.text = session.turn[-1].user_request.interaction.text
        response.taskmap.MergeFrom(session.task.taskmap)

        return response

    
    def domain_retrieve(self, request: QAQuery) -> DocumentList:
        # Retriever
        pass


    
    def synth_response(self, request: QARequest) -> QAResponse:
        
        response: QAResponse = QAResponse()
        query: str = request.query.text
        task_graph: TaskGraph = TaskGraph(request.query.taskmap)

        taskmap_context = self.__build_context(task_graph)

        #get the sentiment classification of the query
        sentiment: Dict = self.__get_sentiment_classification(query)[0]

        if sentiment['label'] == "LABEL_0" or (sentiment['label'] == "LABEL_1" and sentiment["score"] < 0.5):
            response.text = "Sorry, I cannot answer that question."
            return response

        model_input = {
            'question': query,
            'context': taskmap_context
        }
        generated_response = self.qa_model(model_input)

        response.text = generated_response['answer']

        return response