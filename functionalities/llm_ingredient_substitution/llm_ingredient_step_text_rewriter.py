import grpc
import os
import re
import json
import spacy

from compiled_protobufs.llm_pb2_grpc import LLMRunnerStub
from compiled_protobufs.llm_pb2 import (
    AdjustedStepGenerationRequest, AdjustedStepGenerationResponse, ModelBatchRequest
)
from compiled_protobufs.taskmap_pb2 import Session, Task, ReplacedIngredient

from grpc._channel import _InactiveRpcError
from utils import logger
from spacy.matcher import Matcher
from pyserini.analysis import Analyzer, get_lucene_analyzer


class LLMIngredientStepTextRewriter:
    def __init__(self):
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)
        self.nlp = spacy.load("en_core_web_sm")
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))

    def extract_ingredient_name(self, question_text: str, requirements_list) -> str:
        matcher = Matcher(self.nlp.vocab)

        pattern6 = [{'POS': 'ADJ', 'OP': '?'}, {'POS': 'NOUN'}]
        matcher.add("Amounts", [pattern6], greedy="LONGEST")

        processed_step = self.nlp(question_text)

        matches = matcher(processed_step)
        spans = [processed_step[start:end] for _, start, end in matches]

        for item in spans:
            str_item = " ".join(self.analyzer.analyze(str(item))).lower()
            for req in requirements_list:
                if str_item in req.original.name.lower():
                    return str_item
        return ""

    def extract_response(self, generated_answer) -> str:
        valid_dict = {}
        start_token = "{"
        end_token = "}"
        if end_token not in generated_answer:
            return valid_dict

        if start_token in generated_answer:
            generated_answer = "{" + generated_answer.split(start_token)[-1]

        try:
            generated_answer = generated_answer.replace(' \n   ', '').replace('\n', '')
            valid_dict = json.loads(generated_answer)
            logger.info(f'Managed to parse rewritten step text: {valid_dict}')

            if "step_text" in list(valid_dict.keys()):
                return valid_dict
            else:
                logger.info(f'Dictionary contents not valid: {valid_dict}')
        except Exception as e:
            logger.info(f'Could not parse response >{generated_answer}<: {e}')
            return valid_dict

    def process_response_text(self, response_text: str) -> str:
        # remove whitespace
        text = ' '.join(response_text.split("\n"))
        if not re.search(r'[.!?]', text[-1]):
            # If not, add a period (.) to the end of the text
            text += '.'

        # split at punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)

        complete_sentences = []
        for sentence in sentences:
            if sentence.endswith(('.', '!', '?')):
                # remove numbered lists
                sentence = re.sub(r'\d+\.', '', sentence)
                complete_sentences.append(sentence.strip())
        return ' '.join(complete_sentences)

    def build_prompt(self, task_title: str, step_text: str, ingredient: ReplacedIngredient) -> str:
        model_input = f"""Below is an instruction that describes a task, paired with an input that provides further 
        context. Write a response that appropriately completes the request.
        Follow this format: {{\"step_text\": \"\"}}

        ### Instruction: Adjust the step text to replace the original ingredient with the replacement ingredient.

        ### Input:
        Task title:  {task_title}
        Original ingredient: {ingredient.original.amount} {ingredient.original.name}
        Replacement ingredient:{ingredient.replacement.amount} {ingredient.replacement.name}
        Step: {step_text}

        ### Response: {{\"step_text\": \""""
        return model_input

    def adjust_step_texts(self, request: Session) -> Session:
        adjusting_request: AdjustedStepGenerationRequest = AdjustedStepGenerationRequest()
        adjusting_request.task_title = request.task.taskmap.title

        if request.task.phase != Task.TaskPhase.VALIDATING:
            return request

        filtered_ings = {}
        for ing_obj in request.task.taskmap.replaced_ingredients:
            if ing_obj.original.name != "":
                filtered_ings[ing_obj.original.name.lower()] = ing_obj

        q_text = request.turn[-2].user_request.interaction.text
        short_name = self.extract_ingredient_name(q_text, request.task.taskmap.replaced_ingredients)

        # figuring out which parts of the taskmap should be changed
        replaced_ings_steps = {}
        for step in request.task.taskmap.steps:
            for ing_obj in filtered_ings.values():
                if ing_obj.original.name != "" and ing_obj.replacement.name != "":
                    name = ing_obj.original.name
                    if name.lower() in step.response.speech_text.lower() or (
                            short_name in step.response.speech_text.lower() and short_name != ""):
                        adjusting_request.step.append(step)
                        adjusting_request.ingredient.append(ing_obj)
                        replaced_ings_steps[step.unique_id] = ing_obj
                    if name in step.response.screen.requirements:
                        replaced_ings_steps[step.unique_id] = ing_obj

        # generate new steps
        rewritten_steps = {}
        if len(adjusting_request.step) == 0:
            logger.info('Nothing rewritten because no matches in steps')
        else:
            adjusted_step_response: AdjustedStepGenerationResponse = self.rewrite_steps(adjusting_request)
            for step, id in zip(adjusted_step_response.step_text, adjusted_step_response.ids):
                rewritten_steps[id] = step

        # change the taskmap steps
        for idx, step in enumerate(request.task.taskmap.steps):
            new_written_step = rewritten_steps.get(step.unique_id, "")
            if new_written_step != "":
                request.task.taskmap.steps[idx].response.speech_text = new_written_step
                request.task.taskmap.steps[idx].response.screen.paragraphs[0] = new_written_step
                logger.info(f'Rewrote step: {idx + 1}  -> {new_written_step}')

            replaced_ing = replaced_ings_steps.get(step.unique_id, "")

            if replaced_ing != "":
                replaced = False
                str_req = f'{replaced_ing.replacement.amount} {replaced_ing.replacement.name}' if \
                    replaced_ing.replacement.amount != "" else replaced_ing.replacement.name
                for i, req in enumerate(request.task.taskmap.steps[idx].response.screen.requirements):
                    if replaced_ing.original.name in req:
                        request.task.taskmap.steps[idx].response.screen.requirements[i] = str_req.lower()
                        logger.info(f'Replaced ingredient in step {idx + 1}  -> {str_req}')
                        replaced = True
                # if we haven't changed an old req to the new one so far, add it now
                if not replaced and str_req.lower() not in request.task.taskmap.steps[idx].response.screen.requirements:
                    str_req = f'{replaced_ing.replacement.amount} {replaced_ing.replacement.name}' if \
                        replaced_ing.replacement.amount != "" else replaced_ing.replacement.name
                    request.task.taskmap.steps[idx].response.screen.requirements.append(str_req.lower())
                    logger.info(f'Added ingredient in step {idx + 1}  -> {str_req}')

        # change the taskmap requirements
        if short_name != "":
            to_replace = None
            for change_ing in filtered_ings.values():
                if short_name in change_ing.original.name:
                    to_replace = change_ing
                    break

            if to_replace is not None:
                for i, req in enumerate(request.task.taskmap.requirement_list):
                    if short_name in req.name:
                        request.task.taskmap.requirement_list[i].name = to_replace.replacement.name.lower()
                        if to_replace.replacement.amount != "":
                            request.task.taskmap.requirement_list[i].amount = to_replace.replacement.amount
                        logger.info(
                            f'Replaced ingredient in main page on pos {i + 1}  -> {to_replace.replacement.name.lower()}')

        return request

    def rewrite_steps(self, request: AdjustedStepGenerationRequest) -> AdjustedStepGenerationResponse:
        model_batch_request: ModelBatchRequest = ModelBatchRequest()
        model_batch_request.max_tokens = 100

        ids = []

        llm_step_texts: AdjustedStepGenerationResponse = AdjustedStepGenerationResponse()

        try:
            for step, ingredient in zip(request.step, request.ingredient):
                model_input = self.build_prompt(request.task_title, step.response.speech_text, ingredient)
                ids.append(step.unique_id)
                model_batch_request.formatted_prompts.append(model_input)

            llm_responses = self.llm.batch_call_model(model_batch_request)

            for idx, text in enumerate(llm_responses.text):
                llm_step_texts.step_text.append(self.extract_response(text).get('step_text', ''))
                llm_step_texts.ids.append(ids[idx])
            return llm_step_texts
        except _InactiveRpcError as e:
            logger.warning("Step Text Rewriter Channel is down")
            return llm_step_texts
