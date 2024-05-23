import grpc
import os
import json

from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub
from compiled_protobufs.llm_pb2 import (
    IngredientReplacementRequest,
    IngredientReplacementResponse,
    ModelRequest,
    ModelResponse,
)
from compiled_protobufs.taskmap_pb2 import Ingredient

from utils import logger


def extract_replacement_response(generated_answer: str, original_ing: Ingredient) -> dict:
    valid_dict = {}
    end_token = "}"
    # the part of the response format included in the prompt
    prefix = "{\"name\""
    if end_token not in generated_answer:
        return valid_dict

    generated_answer = f"{prefix}{generated_answer}"

    try:
        generated_answer = generated_answer.replace(" \n   ", "").replace("\n", "")
        valid_dict = json.loads(generated_answer)
        logger.info(f"Managed to parse ingredient: {valid_dict}")

        if "name" in list(valid_dict.keys()) and "amount" in list(valid_dict.keys()):
            return valid_dict
        else:
            logger.debug(f"Dictionary contents not valid: {valid_dict}")

    except Exception as e:
        if '"amount"' in generated_answer and "name" in generated_answer:
            try:
                first_part = generated_answer.split(",")[0] + "}"
                valid_dict = json.loads(first_part)
                if "}" in generated_answer:
                    second_part = generated_answer.split('"amount"')[1].replace(":", "").replace("}", "").strip()
                    valid_dict["amount"] = second_part
                    logger.info(f"Managed to parse ingredient (2nd try): {valid_dict}")
                    return valid_dict
                else:
                    second_part = generated_answer.split('"amount"')[1]
                    if second_part.replace(":", "").strip() in original_ing.name:
                        valid_dict["amount"] = original_ing.name
                        logger.info(f"Managed to parse ingredient (3rd try): {valid_dict}")
                        return valid_dict
                    if second_part.replace(":", "").strip() in original_ing.amount:
                        valid_dict["amount"] = original_ing.amount
                        logger.info(f"Managed to parse ingredient (3rd try): {valid_dict}")
                        return valid_dict
            except Exception as e:
                logger.debug(f"Second parsing did not work.")
        return valid_dict


class LLMIngredientSubstitutionGenerator:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)

    @staticmethod
    def build_prompt(request: IngredientReplacementRequest) -> ModelRequest:
        model_request: ModelRequest = ModelRequest()

        if request.original_ingredient.name != "":
            original_ing = f"Original ingredient: {request.original_ingredient.amount} {request.original_ingredient.name}\n"
        else:
            original_ing = ""
        orginal_ing_amount = "" if request.original_ingredient.amount == "" else request.original_ingredient.amount

        prompt = (
            f"### Instruction: You are a friendly AI assistant who is assisting a human making "
            f"{request.task_title}. You are helping the user to replace an ingredient in the recipe. "
            f"If the amount is not specified in your earlier suggestion, extract the amount from the "
            f"original ingredient. If your earlier suggestion responds that this substitution is not possible, "
            f"please respond with an empty ingredient.\n "
            f'Respond in this format: {{"name": "", "amount": "{orginal_ing_amount}"}}\n\n '
            f"### Input:\n{original_ing}"
            f"User: {request.user_question}\n"
            f"Your suggestion: {request.agent_response}\n\n"
            f'### Response:{{"name"'
        )

        model_request.formatted_prompt = prompt
        model_request.max_tokens = 20
        return model_request

    def generate_replacement(self, request: IngredientReplacementRequest) -> IngredientReplacementResponse:
        model_request = self.build_prompt(request)

        llm_response: ModelResponse = self.llm.call_model(model_request)

        llm_replacement: IngredientReplacementResponse = IngredientReplacementResponse()
        parsed_result = extract_replacement_response(llm_response.text, request.original_ingredient)
        logger.info(parsed_result)
        if parsed_result == {}:
            return llm_replacement
        ingredient: Ingredient = Ingredient()
        ingredient.name = parsed_result.get("name", "")
        ingredient.amount = str(parsed_result.get("amount", ""))

        llm_replacement.new_ingredient.MergeFrom(ingredient)
        return llm_replacement
