import torch
import random

from .abstract_qa import AbstractQA
from taskmap_pb2 import Session, Task, TaskMap
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList
from .numbers import NumberSanitizer
from task_graph import TaskGraph

from utils import (
    logger,
    Downloader,
)

from transformers import set_seed, AutoTokenizer, pipeline, AutoModelForSeq2SeqLM
from typing import Dict, List


def get_recommendations(candidates: List[TaskMap], domain):
    """Generate recommendation based on TaskMaps metadata.

    Given a list of TaskMaps, this method generates a string with a
    reccomentation based on the TaskMaps' metadata, namely the duration
    and rating of the tasks. The returned recommendation string is then
    attached to the speech_text string in the populate_choices() method.

    Args:
        candidates (List[TaskMap]): a list of TaskMap objects

    Returns:
        Recommendation_string: A string containing the recommendation
        based on duration or rating. If neither is available, a random
        option is suggested.
    """
    preference = ["My personal favourite is option ", "My top pick would be option ", "I would recommend option ",
                  "I would choose option ", "I prefer option ", "I would go with option "]
    preference_questions = ["Why don't we go with option ", "Would you like option ", "Why not try option "]
    preference_rating = [
        [f"{random.choice(preference)}", ". It received the highest rating and I think you could like it! "],
        [f"{random.choice(preference)}", ". It has the best rating! "], \
        ["I really enjoy option ", " and clearly others do too! "],
        ["Option ", " is quite popular among other users. "],
        [f"{random.choice(preference_questions)}", "? The reviews are very good! "]]
    preference_time = ["if you are short on time, go for number", "if you are in a rush, choose option", \
                       "if you're pressed for time, try option "]
    preference_duration = [[f"{random.choice(preference)}", " because it is the quickest. "],
                           [f"{random.choice(preference)}", " because it does not take a lot of time. "], \
                           [f"{random.choice(preference)}",
                            " because it is done quickly and you can enjoy it sooner! "]]
    preference_random_cooking = [[f"{random.choice(preference)}",
                                  ". It is known for its exceptional flavors. I think you'll really enjoy it! "], \
                                 [f"{random.choice(preference)}", ". It looks really tasty! "],
                                 [f"{random.choice(preference_questions)}", "? It looks really tasty!"],
                                 ["Option ", "has a great blend of flavours. Why not try that one? Yum!"]]
    preference_random_diy = [
        [f"{random.choice(preference)}", " because it’s good for both beginners and experienced DIYers! "],
        [f"{random.choice(preference)}", " because you need less specialised tools"], \
        [f"{random.choice(preference_questions)}", "? It seems to be what you are looking for!"]]

    metadata = {}
    for idx, candidate in enumerate(candidates[:3]):
        if candidate.HasField('task'):
            metadata[idx] = {"rating": candidate.task.rating_out_100, "duration": candidate.task.total_time_minutes,
                         "tags": candidate.task.tags}
        else:
            metadata[idx] = {"rating": None, "duration": None, "tags": []}

    ratings = [metadata[i]["rating"] for i in metadata if metadata[i]["rating"] is not None]
    durations = [metadata[i]["duration"] for i in metadata if metadata[i]["duration"] is not None]

    max_rating_index = None
    if ratings:
        max_rating_index = max(metadata, key=lambda i: metadata[i]["rating"] if metadata[i]["rating"] is not None else float('-inf'))
        if len(ratings) == 1:
            max_rating_index = next(iter(metadata))

    min_duration_index = None
    if durations:
        min_duration_index = min(metadata, key=lambda i: metadata[i]["duration"] if metadata[i]["duration"] is not None else float('-inf'))
        if len(durations) == 1:
            min_duration_index = next(iter(metadata))

    rating_prompt = random.choice(preference_rating)
    time_prompt = f" However, {random.choice(preference_time)} {min_duration_index + 1} . "
    duration_prompt = random.choice(preference_duration)
    random_prompt_cooking = random.choice(preference_random_cooking)
    random_prompt_diy = random.choice(preference_random_diy)

    recommendation_string = ""

    if max_rating_index is not None:
        recommendation_string = f"{rating_prompt[0]} {max_rating_index + 1}{rating_prompt[1]}"
        if min_duration_index is not None and max_rating_index != min_duration_index:
            recommendation_string += f"{time_prompt}"
    elif min_duration_index is not None:
        recommendation_string = f"{duration_prompt[0]} {min_duration_index + 1}{duration_prompt[1]}"
    else:
        if domain == Session.Domain.COOKING:
            recommendation_string = f"{random_prompt_cooking[0]} {random.randint(1, 3)}{random_prompt_cooking[1]}"
        if domain == Session.Domain.DIY:
            recommendation_string = f"{random_prompt_diy[0]} {random.randint(1, 3)}{random_prompt_diy[1]}"

    max_rating = candidates[max_rating_index] if max_rating_index is not None else None
    min_duration = candidates[min_duration_index] if min_duration_index is not None else None
    if recommendation_string == "":
        recommendation_string = "I don't have a recommendation. "

    return recommendation_string, max_rating, min_duration


class NeuralIntraTaskMapContextualQA(AbstractQA):

    def __init__(self) -> None:

        set_seed(42)

        device: int = -1 if not torch.cuda.is_available() else 0
        logger.info(f"Cuda found: {torch.cuda.is_available()}")

        qa_model_name = "google/flan-t5-base"
        sa_model_name = "cardiffnlp/twitter-roberta-base-sentiment"

        artefact_ids = ["task_question_answering", "sentiment_analysis"]
        downloader = Downloader()
        downloader.download(artefact_ids)

        qa_model_path = downloader.get_artefact_path(artefact_ids[0])
        sa_model_path = downloader.get_artefact_path(artefact_ids[1])

        self.tokenizer = AutoTokenizer.from_pretrained(qa_model_name, cache_dir=qa_model_path)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(qa_model_name, cache_dir=qa_model_path)

        logger.info("Loaded Task QA model")

        self.sentiment_classifier = pipeline('sentiment-analysis', 
                            model=sa_model_name, 
                            model_kwargs = {"cache_dir": sa_model_path}, 
                            device = device)
        logger.info("Loaded Sentiment Analysis model")

        self.sanitizer = NumberSanitizer()

    @staticmethod
    def __sanitize(text: str) -> str:
        # replace all weird characters like "`", "\n", "\r", "\t" with a space
        text = text.replace("`", " ")
        text = text.replace("\\", "")
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        # remove all non ascii characters
        text = text.encode("ascii", errors="ignore").decode()
        # strip all newlines
        text = text.strip('\n')
        text = text.replace("  ", " ")
        text = text.replace("#", "")
        if "taskbot" in text.lower():
            text = text.lower().replace("taskbot", "")
            text = text.replace(":", "")
        return text.strip()

    def __get_sentiment_classification(self, question: str) -> List[Dict]:
        """
        Run sentiment analysis on the User's query to assess how dangerous it is
        """

        with torch.no_grad():
            return self.sentiment_classifier(question)

    @staticmethod
    def strip_newlines(text):
        return text.replace('\n', " ").replace("  ", " ")

    def __build_context_task_selected(self, task_graph: TaskGraph, query: str) -> str:

        context = []

        context.append(f"The title of this is {self.strip_newlines(task_graph.title)}.")
        if task_graph.author != "":
            context.append(f"The author is called {self.strip_newlines(task_graph.author)}.")
        else:
            context.append(f"It was published by {self.strip_newlines(task_graph.domain_name)}.")
        if task_graph.total_time_minutes != 0:
            context.append(
                f"The total time in minutes to work through the instructions is: {task_graph.total_time_minutes} minutes.")
        context.append(f"The instruction have a rating of {task_graph.rating_out_100 / 20} out of 5.")

        step_count = 0
        requirements = 'Requirements/Ingredients: '
        for key, value in task_graph.node_set.items():
            if value.__class__.__name__ == "RequirementNode":
                requirements += value.amount + ' ' + value.name + '; '
            if value.__class__.__name__ == "ExecutionNode":
                step_count += 1
        if step_count > 0:
            context.append(f"There are {step_count} steps")
        if task_graph.serves != "":
            context.append(f"The instructions make up a serving of {self.strip_newlines(task_graph.serves)}.")
        
        context.append(requirements)

        return "\n".join(context)

    def build_candidates_context(self, candidates):
        candidates_str_list = []
        count = 1
        for cand in candidates:
            if cand.HasField("task"):
                cand = cand.task
                cand_str = f'Option {count} is {self.strip_newlines(cand.title)} '
                if cand.author != "":
                    cand_str += f"by {self.strip_newlines(cand.author)}, "
                if cand.total_time_minutes != 0:
                    cand_str += f"which takes {cand.total_time_minutes} minutes "
                if cand.rating_out_100 != 0:
                    cand_str += f"and has a rating of {cand.rating_out_100 / 20} out of 5."
                count += 1
                candidates_str_list.append(cand_str)

        return " ".join(candidates_str_list)

    def __build_context_general(self, request) -> str:

        context = []

        candidates = request.query.task_selection.candidates_union[request.query.task_selection.results_page:
                                                             request.query.task_selection.results_page+3]

        if len(candidates) > 0 and request.query.phase == Task.TaskPhase.PLANNING:
            # need to compare tasks now

            rec_string, max_rating_cand, min_duration_cand = get_recommendations(
                [cand for cand in candidates], request.query.domain
            )

            context.append(self.build_candidates_context(candidates))
            context.append(rec_string)

            if max_rating_cand and max_rating_cand.HasField("task"):
                context.append(f"The best rated option is {max_rating_cand.task.title}. ")
            if min_duration_cand and min_duration_cand.HasField("task"):
                context.append(f"The quickest option is {min_duration_cand.task.title}. ")

        if request.query.task_selection.theme.theme != "":
            context.append(f"The current theme is {request.query.task_selection.theme}. ")
            if request.query.task_selection.theme.description != "":
                context.append(f"The theme description is: {request.query.task_selection.theme}. ")
        if request.query.task_selection.category.title != "":
            context.append(f"The current category is {request.query.task_selection.theme}. ")
            if request.query.task_selection.category.description != "":
                context.append(f"The category description is: {request.query.task_selection.theme}. ")

        return "\n".join(context)

    def rewrite_query(self, session: Session) -> QAQuery:
        # Query is the last turn utterance, top K not needed for this imp.
        response: QAQuery = QAQuery()
        response.text = session.turn[-1].user_request.interaction.text
        response.taskmap.MergeFrom(session.task.taskmap)

        return response

    def domain_retrieve(self, request: QAQuery) -> DocumentList:
        # Retriever
        pass

    def __rewrite_response(self, qa_response: str, request: QARequest) -> str:
        candidates_titles = [cand.task.title if cand.HasField("task") else cand.category.title for cand in request.query.task_selection.candidates_union]
        for idx, title in enumerate(candidates_titles):
            qa_response = qa_response.replace(title, f"Option {idx+1} which is: {title}.")
        qa_response = self.__sanitize(qa_response)
        return qa_response

    def synth_response(self, request: QARequest) -> QAResponse:

        response: QAResponse = QAResponse()
        query: str = request.query.text
        task_graph: TaskGraph = TaskGraph(request.query.taskmap)

        if request.query.taskmap.title == "":
            taskmap_context = self.__build_context_general(request)
        else:
            taskmap_context = self.__build_context_task_selected(task_graph, query)
            if request.query.phase == Task.TaskPhase.EXECUTING:
                task_state = request.query.state
                step_id = task_state.execution_list[task_state.index_to_next-1]
                current_step = task_graph.get_node(step_id)
                taskmap_context += f'\nThis is the current step: {current_step.response.speech_text}'
                
        taskmap_context += f'\n Conversation History:\nUser: {request.query.conv_hist_user}\n' \
                           f'Taskbot: {request.query.conv_hist_bot}'
        
        # get the sentiment classification of the query
        sentiment: Dict = self.__get_sentiment_classification(query)[0]

        if sentiment['label'] == "LABEL_0" or (sentiment['label'] == "LABEL_1" and sentiment["score"] < 0.5):
            response.text = "Sorry, I cannot answer that question."
            return response

        instruction = "Answer the following question in a full sentence with context. If the answer is not in the " \
                      "context, just say I do not know "

        model_input = f"Context: {taskmap_context}\n{instruction}\nQuestion: {query}"
        input_ids = self.tokenizer(model_input, return_tensors="pt").input_ids
        outputs = self.model.generate(input_ids, max_length=128)
        qa_model_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        qa_model_response = self.__rewrite_response(qa_model_response, request)

        if qa_model_response.lower() == "i do not know":
            response.text = ""
        else:
            response.text = qa_model_response
        
        return response
