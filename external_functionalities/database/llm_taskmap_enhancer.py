import os
import grpc
import random

from taskmap_pb2 import TaskMap
from llm_pb2 import MultipleSummaryGenerationRequest, ProactiveQuestionGenerationRequest
from llm_pb2_grpc import LLMSummaryGenerationStub, LLMProactiveQuestionGenerationStub
from utils import logger


class LLMTaskMapEnhancer:
    def __init__(self):
        functionalities_channel = grpc.insecure_channel(
            os.environ['FUNCTIONALITIES_URL'])
        self.llm_summary_generator = LLMSummaryGenerationStub(
            functionalities_channel)
        self.llm_proactive_question_generator = LLMProactiveQuestionGenerationStub(
            functionalities_channel)

    def enhance_taskmap(self, taskmap: TaskMap, staged_db) -> TaskMap:
        steps = taskmap.steps
        grouped_steps = [steps[i:i+3] for i in range(0, len(steps), 3)]
        output = staged_db.get(taskmap.taskmap_id)

        for group in grouped_steps:
            request: MultipleSummaryGenerationRequest = MultipleSummaryGenerationRequest()
            for step in group:
                request.task_title.append(taskmap.title)
                request.step_text.append(step.response.speech_text)
                request.more_details.append(step.response.description)
            summaries = self.llm_summary_generator.generate_summaries(request)
            for i, step in enumerate(group):
                step.response.speech_text = summaries.summary[i]
            output.taskmap.ParseFromString(taskmap.SerializeToString())
            staged_db.put(output)
            
        taskmap = self.proactive_question_enhancement(taskmap, staged_db)
        
        return taskmap

    @staticmethod
    def __get_indices_with_criteria(length):
        num_indices = 5 if length >= 8 else (length-3 if length >= 3 else 0)
        left_indices = set(list(range(2,length-1)))
        indices = set()
        while len(indices) < num_indices:
            index = random.choice(list(left_indices))
            indices.add(index)
            left_indices.remove(index)

        return list(indices)

    def proactive_question_enhancement(self, taskmap, staged_db):
        logger.info("GENERATE QUESTIONS")
        request: ProactiveQuestionGenerationRequest = ProactiveQuestionGenerationRequest()
        indices = self.__get_indices_with_criteria(len(taskmap.steps))

        if indices == []:
            return taskmap
        
        for ind in indices:
            request.task_title.append(taskmap.title)
            request.current_step.append(taskmap.steps[ind].response.speech_text)
            request.previous_steps.append("- " + "\n- ".join([el.response.speech_text for el in taskmap.steps[ind-2:ind]]))
        
        response = self.llm_proactive_question_generator.generate_proactive_question(request)
        questions = response.questions
        
        for i, question in enumerate(questions):
            taskmap.steps[indices[i]].response.screen.extra_information.append(question)
            
        output = staged_db.get(taskmap.taskmap_id)
        output.taskmap.ParseFromString(taskmap.SerializeToString())
        staged_db.put(output)
        return taskmap
