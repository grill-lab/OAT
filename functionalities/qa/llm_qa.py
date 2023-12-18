import os
import grpc
import time
import random
import re
import spacy

from grpc._channel import _InactiveRpcError
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from typing import List

from taskmap_pb2 import Session, Task, ExecutionStep
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList
from llm_pb2 import ModelRequest, ModelResponse
from llm_pb2_grpc import LLMRunnerStub
from .abstract_qa import AbstractQA

from chitchat_classifier_pb2 import ChitChatResponse

from task_graph import TaskGraph
from utils import (
    logger, HELPFUL_PROMPT_PAIRS, DEFAULT_QA_PROMPTS, REPLACE_SUGGESTION, NOT_POSSIBLE
)


def process_response_text(response_text: str) -> str:
    # remove whitespace
    text = ' '.join(response_text.split("\n"))

    # split at punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    complete_sentences = [sentence.strip() for sentence in sentences]
    return ' '.join(complete_sentences)


class LLMQA(AbstractQA):

    def __init__(self, environ_var: str):
        self.endpoint_var = environ_var
        llm_channel = grpc.insecure_channel(os.environ["LLM_FUNCTIONALITIES_URL"])
        self.llm = LLMRunnerStub(llm_channel)
        self.nlp = spacy.load("en_core_web_sm")
        logger.info('LLM QA SpaCy initialized')

    @staticmethod
    def __get_helpful_prompt(user_query: str) -> str:
        for word in user_query.split(" "):
            for keyword, answer in HELPFUL_PROMPT_PAIRS:
                if word == keyword:
                    return answer

        for keyword, answer in HELPFUL_PROMPT_PAIRS:
            if keyword in user_query:
                return answer

    def process_last_sentence(self, last_sentence: str) -> str:

        if last_sentence.endswith(('.', '!', '?')):
            return last_sentence

        doc = self.nlp(last_sentence)

        for i in range(1, len(doc)):
            last_token = doc[-i]
            if last_token.pos_ not in ["ADJ", "NOUN"] and last_token.dep_ not in ["pobj"]:
                last_sentence = f"{last_token.text}".join(last_sentence.split(last_token.text)[:-1])
            else:
                break

        if len(last_sentence.split(" ")) < 3:
            return ""

        if last_sentence.endswith((',', ":", ";")):
            last_sentence[-1] = "."

        return f" {last_sentence}".strip()

    def extract_qa_answer(self, generated_answer):
        start_token = "Your response: "
        end_token_1 = "Human"
        end_token_2 = "#"
        if start_token in generated_answer:
            generated_answer = generated_answer.split(start_token)[-1]
        if end_token_2 in generated_answer:
            generated_answer = generated_answer.split(end_token_2)[0]
        if end_token_1 in generated_answer:
            generated_answer = generated_answer.split(end_token_1)[0]
        generated_answer = generated_answer.replace('\n', " ")

        # if generated answer does not end with punctuation, check whether there is a "that" in it and split rest off
        generated_answer_sentences = generated_answer.split(". ")
        final_answer = generated_answer_sentences[:-1]
        final_answer.append(self.process_last_sentence(generated_answer_sentences[-1]))

        return ". ".join(final_answer).strip()

    def rewrite_query(self, session: Session) -> QAQuery:
        pass

    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        pass

    @staticmethod
    def strip_newlines(text):
        return text.replace('\n', " ").replace("  ", " ")

    def __build_context_task_selected(self, task_graph: TaskGraph, query: str, question_type: str) -> str:

        context = []

        if task_graph.author != "":
            context.append(f"The author is called {self.strip_newlines(task_graph.author)}.")
        else:
            context.append(f"It was published by {self.strip_newlines(task_graph.domain_name)}.")

        step_count = 0
        requirements = 'This is what the user needs: '
        for key, value in task_graph.node_set.items():
            if value.__class__.__name__ == "RequirementNode":
                requirements += value.amount + ' ' + value.name + '; '
            if value.__class__.__name__ == "ExecutionNode":
                step_count += 1

        if question_type == "ingredient question":
            context.append(requirements)

            if task_graph.serves != "" and task_graph.serves != "None":
                context.append(f"The instructions make up a serving of {self.strip_newlines(task_graph.serves)}.")
            else:
                context.append(f"The task does not specify for how many people it is. ")
            if task_graph.rating_out_100 != 0:
                context.append(f"The instruction have a rating of {task_graph.rating_out_100 / 20} out of 5.")

        elif question_type == "step question" and step_count > 0:
            context.append(f"There are {step_count} steps. ")
            if task_graph.total_time_minutes != 0:
                context.append(f"The total time is {task_graph.total_time_minutes} minutes.")

        return "\n".join(context)

    def build_candidates_context(self, candidates, question_type):
        candidates_str_list = ["You are helping the user choose between the following options:"]
        count = 1

        time_place_holders = ["which has no time estimate ", "which has no time estimate ",
                              "which has no time estimate "]
        for idx, cand in enumerate(candidates):
            if cand.HasField("task"):
                cand = cand.task
                cand_str = f'Option {count} is {self.strip_newlines(cand.title)} '
                if question_type == 'current viewing options question':
                    if cand.author != "":
                        cand_str += f"by {self.strip_newlines(cand.author)}, "
                    if cand.total_time_minutes != 0:
                        time_place_holders[idx] = f"which takes {cand.total_time_minutes} minutes "
                    cand_str += "{" + f"{idx}" + "}"
                    if cand.rating_out_100 != 0:
                        cand_str += f"and has a rating of {cand.rating_out_100 / 20} out of 5."
                count += 1
                candidates_str_list.append(cand_str)
            else:
                candidates_str_list.append(f'The third option is a category called {cand.category.title}. ')
                count += 1
        candidates_str_list.append('Respond to the human or ask a question back.')
        candidates_str_list.append('Include a reason why you recommend an option.')

        if any([prompt for prompt in time_place_holders if prompt != "which has no time estimate "]):
            return " ".join(candidates_str_list).format(*time_place_holders)
        else:
            return " ".join(candidates_str_list).format("", "", "")

    def __build_context_general(self, request) -> str:
        context = []

        if request.query.task_selection.theme.theme != "":
            context.append(f"The current theme is {request.query.task_selection.theme.theme}. ")
            if request.query.task_selection.theme.description != "":
                context.append(f"The theme description is: {request.query.task_selection.theme.description}. ")
        if request.query.task_selection.category.title != "":
            context.append(f"The current category is {request.query.task_selection.category.title}. ")
            if request.query.task_selection.category.description != "":
                context.append(f"The category description is: {request.query.task_selection.category.description}. ")

        candidates = request.query.task_selection.candidates_union[request.query.task_selection.results_page:
                                                                   request.query.task_selection.results_page + 3]

        has_category = any([cand.HasField("category") for cand in candidates[
                                                                  request.query.task_selection.results_page: request.query.task_selection.results_page + 3]])

        if len(candidates) > 0 and request.query.phase == Task.TaskPhase.PLANNING \
                and request.question_type in ["current viewing options question"]:
            if request.query.task_selection.category.title == "":
                # need to compare tasks now
                context.append(self.build_candidates_context(candidates, request.question_type))

                if has_category:
                    context.append('You should recommend the third option if the user seems unsure. ')
            else:
                # need to compare subcategories now
                sub_categories = request.query.task_selection.category.sub_categories
                for idx, cand in enumerate(sub_categories):
                    context.append(f"Option {idx + 1} is {cand.title}. ")

        if len(context) == 0:
            return ""

        return " ".join(context)

    def build_prompt(self, request: QARequest) -> ModelRequest:

        task_graph: TaskGraph = TaskGraph(request.query.taskmap)
        user_question: str = request.query.text
        model_request: ModelRequest = ModelRequest()
        taskmap_context = ""

        logger.info(f'QUESTION TYPE: {request.question_type}')

        prompt = "### Instruction: \n"

        if request.query.taskmap.title == "":
            taskmap_context = self.__build_context_general(request)
            prompt += f'You are a friendly AI assistant who is assisting a human. '
            if request.question_type in ['current viewing options question']:
                pass
            else:
                prompt += f'You specialize in cooking, arts & crafts, and DIY. You do not reveal your name in ' \
                          f'the spirit of fair competition. '
            prompt += 'Answer the given user question concisely or ask a question back. \n'

        else:
            prompt += f'You are a friendly AI assistant who is assisting a human making {request.query.taskmap.title}. '

            if request.question_type not in ['general cooking or DIY question'] \
                    and request.query.text != "more details":
                taskmap_context = self.__build_context_task_selected(task_graph, user_question,
                                                                     question_type=request.question_type)

            if request.query.phase == Task.TaskPhase.EXECUTING:
                if request.query.text == "more details":
                    prompt += "Based on the current step, give more details. "
                else:
                    prompt += 'Answer the given user question concisely or ask a question back. '
                task_state = request.query.state
                step_id = task_state.execution_list[task_state.index_to_next - 1]
                current_step: ExecutionStep = task_graph.get_node(step_id)
                if len(" ".join(current_step.response.screen.paragraphs).split(" ")) <= 100:
                    taskmap_context += f'\nThis is the current step: {" ".join(current_step.response.screen.paragraphs)}'
                else:
                    taskmap_context += f'\nThis is the current step: {" ".join(current_step.response.speech_text)}'

        if request.query.last_intent in ["NextIntent", "RepeatIntent", "PreviousIntent", "ChitChatIntent"] or \
                any([prompt for prompt in DEFAULT_QA_PROMPTS if prompt in request.query.conv_hist_bot]) or \
                any([prompt for prompt in NOT_POSSIBLE if prompt in request.query.conv_hist_bot]):
            pass
        elif request.query.text != "more details":
            taskmap_context += "\nYou just had the following conversation: \n"
            taskmap_context += f'Human: {request.query.conv_hist_user} \n'

            if request.query.last_intent in ["QuestionIntent"] or \
                    any([set_prompt for set_prompt in REPLACE_SUGGESTION if set_prompt in request.query.conv_hist_bot]):
                for set_prompt in REPLACE_SUGGESTION:
                    if set_prompt in request.query.conv_hist_bot:
                        request.query.conv_hist_bot = request.query.conv_hist_bot.split(set_prompt)[0]
                        break

            if len(request.query.conv_hist_bot) > 20:
                sentences = re.split(r'(?<=[.!?])\s+', request.query.conv_hist_bot)
                taskmap_context += f'You: {" ".join(sentences[:2])} \n'
            else:
                taskmap_context += f'You: {request.query.conv_hist_bot} \n'

        if taskmap_context != "":
            prompt += f'{taskmap_context}\n\n'
        if request.question_type == "ingredient substitution" and user_question.startswith(
                "replace") or user_question.startswith("substitute"):
            user_question = f'With what can I {user_question}?'

        prompt += f"### Input: Human: {user_question} \n\n ### Response: Your response:"

        model_request.formatted_prompt = prompt
        model_request.max_tokens = 35

        return model_request

    def call_llm_qa(self, request: QAQuery) -> ChitChatResponse:
        model_request = self.build_prompt(request)
        llm_response: ModelResponse = self.llm.call_model(model_request)
        logger.info(llm_response.text)

        agent_response: QAResponse = QAResponse()
        extracted_answer = self.extract_qa_answer(llm_response.text)
        agent_response.text = process_response_text(extracted_answer)
        if agent_response.text != "":
            logger.info(f'EXTRACTED QA RESPONSE: {agent_response.text}')

        return agent_response

    def generate_qa_response(self, request: QARequest, default_timeout=1500) -> QAResponse:
        # CALL LLM SERVICE FROM HERE

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.call_llm_qa, request)
            timeout: float = default_timeout / 1000 + time.monotonic()
            try:
                if future.done() or timeout - time.monotonic() > 0:
                    response = future.result(timeout=timeout - time.monotonic())
                    return response

                else:
                    future.cancel()
                    logger.warning(f"Timeout for LLM QA")
                    response = QAResponse()
                    response.text = ""
                    return response

            except TimeoutError as e:
                future.cancel()
                logger.warning("TimeoutError while running LLM QA", exc_info=e)
                response = QAResponse()
                response.text = ""
                return response

            except _InactiveRpcError as e:
                future.cancel()
                logger.warning("LLM Channel is down")
                response = QAResponse()
                response.text = ""
                return response

            except Exception as e:
                future.cancel()
                logger.info(e)
                response = QAResponse()
                response.text = ""
                return response

    def synth_response(self, request: QARequest) -> QAResponse:
        qa_response = self.generate_qa_response(request)
        user_question = request.query.text

        if qa_response.text != "":
            if not qa_response.text[-1] in [".", ":", ",", "?", "!"]:
                qa_response.text = qa_response.text.strip()
                qa_response.text += "."  # add a period at the end of the sentence

            keyword_helpful_prompt = self.__get_helpful_prompt(user_question)
            transition_options = ['But anyway', 'Just wanted to say', 'Just so you know', 'Just to let you know',
                                  'By the way']
            if keyword_helpful_prompt:
                qa_response.text = f'{qa_response.text} {random.choice(transition_options)} {keyword_helpful_prompt.lower()}. '

        return qa_response
