import grpc
import os
import random
import spacy

from utils import logger, REPLACE_SUGGESTION, jaccard_sim, NOT_POSSIBLE, indri_stop_words

from qa_pb2 import QARequest, QAResponse
from llm_pb2 import IngredientReplacementRequest, IngredientReplacementResponse
from llm_pb2_grpc import LLMReplacementGenerationStub
from taskmap_pb2 import ReplacedIngredient, Ingredient

from grpc._channel import _InactiveRpcError
from spacy.matcher import Matcher
from pyserini.analysis import Analyzer, get_lucene_analyzer
from typing import Tuple


class SubstitutionHelper:
    def __init__(self):
        channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
        self.replacement_generator = LLMReplacementGenerationStub(channel)
        self.nlp = spacy.load("en_core_web_sm")
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))

    def includes_amount(self, qa_response: QAResponse):
        matcher = Matcher(self.nlp.vocab)

        pattern1 = [{'POS': 'NUM'}, {'POS': 'NUM', 'OP': '?'}, {'POS': 'NOUN'}]
        pattern2 = [{'POS': 'NUM'}, {'POS': 'NUM', 'OP': '?'}, {"ORTH": "-", 'OP': '?'}, {'POS': 'NOUN'}]
        pattern3 = [{'POS': 'NUM'}, {"TEXT": {"REGEX": "^\d+(?:/\d+)?-\w+$"}}]
        pattern4 = [{'POS': 'NUM'}, {'POS': 'NUM'}, {"TEXT": {"REGEX": "^\d+(?:/\d+)?-\w+$"}}]
        pattern5 = [{'POS': 'NUM'}]

        matcher.add("Amounts", [pattern1, pattern2, pattern3, pattern4, pattern5], greedy="LONGEST")

        processed_texts = self.nlp(qa_response.text)

        matches = matcher(processed_texts)
        spans = [processed_texts[start:end] for _, start, end in matches]

        if len(spans) > 0:
            return True
        else:
            return False

    def get_original_ingredient(self, request: QARequest) -> Ingredient:
        matcher = Matcher(self.nlp.vocab)

        pattern6 = [{'POS': 'ADJ', 'OP': '?'}, {'POS': 'NOUN'}]
        matcher.add("Amounts", [pattern6], greedy="LONGEST")

        processed_step = self.nlp(request.query.text)

        matches = matcher(processed_step)
        spans = [processed_step[start:end] for _, start, end in matches]

        extracted_ings = []
        for item in spans:
            str_item = " ".join(self.analyzer.analyze(str(item))).lower()
            for req in request.query.taskmap.requirement_list:
                if str_item in req.name.lower():
                    ing: Ingredient = Ingredient()
                    ing.amount = req.amount
                    ing.name = req.name
                    ing.name = ing.name.replace(req.amount, "").strip()
                    extracted_ings.append(ing)

        additional_stop_words = ["can", "i", "you", "replace", "substitute", "the", "with"]
        filtered_question = " ".join(
            [word for word in request.query.text.lower().split() if word not in additional_stop_words])
        filtered_question = " ".join([word for word in filtered_question.split() if word not in indri_stop_words])
        filtered_question = " ".join(self.analyzer.analyze(str(filtered_question))).lower()

        if len(extracted_ings) == 0:
            for word in filtered_question.split(" "):
                for req in request.query.taskmap.requirement_list:
                    if word in req.name.lower():
                        ing: Ingredient = Ingredient()
                        ing.amount = req.amount
                        ing.name = req.name
                        ing.name = ing.name.replace(req.amount, "").strip()
                        extracted_ings.append(ing)

        if len(extracted_ings) > 1:
            scores = []
            for ing in extracted_ings:
                score = jaccard_sim(" ".join(self.analyzer.analyze(ing.name)).lower(), filtered_question)
                logger.info(f'{ing.name} score: {score}')
                scores.append(score)
            return extracted_ings[scores.index(max(scores))]
        elif len(extracted_ings) == 1:
            return extracted_ings[0]
        return Ingredient()

    def generate_replacement(self, request: QARequest, response: QAResponse) -> Tuple[Ingredient, Ingredient]:
        replacement_request: IngredientReplacementRequest = IngredientReplacementRequest()
        replacement_request.task_title = request.query.taskmap.title
        replacement_request.user_question = request.query.text
        replacement_request.agent_response = response.text
        original_req = self.get_original_ingredient(request)
        if not self.includes_amount(response):
            replacement_request.original_ingredient.MergeFrom(original_req)
        try:
            replacement: IngredientReplacementResponse = self.replacement_generator.generate_replacement(
                replacement_request)
            return replacement.new_ingredient, original_req
        except _InactiveRpcError as e:
            logger.info(e)
            logger.warning("Replacement LLM Channel is down")
            return Ingredient(), Ingredient()

    def create_substitution_idea(self, request, qa_response):
        replacement_ingredient, original_ingredient = self.generate_replacement(request, qa_response)
        if replacement_ingredient.name != "":
            if original_ingredient.name.lower() != replacement_ingredient.name.lower():
                if original_ingredient.name != "":
                    qa_response.text = f'{qa_response.text} {random.choice(REPLACE_SUGGESTION)} {replacement_ingredient.name}. Say yes if you want me to do that.'
                    replaced_ing = ReplacedIngredient()
                    replaced_ing.original.MergeFrom(original_ingredient)
                    replaced_ing.replacement.MergeFrom(replacement_ingredient)
                    qa_response.replacement.MergeFrom(replaced_ing)
                else:
                    if qa_response.text != "no":
                        qa_response.text = f'{qa_response.text} {random.choice(NOT_POSSIBLE)}'
                    else:
                        qa_response.text = random.choice(NOT_POSSIBLE)
            else:
                qa_response.text = f'{qa_response.text}'

        logger.info(qa_response)

        return qa_response
