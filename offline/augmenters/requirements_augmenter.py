import spacy

from taskmap_pb2 import OutputInteraction, ScreenInteraction
from task_graph.nodes.requirement_node import RequirementNode
from .abstract_step_augmenter import AbstractSimpleStepAugmenter
from taskmap_pb2 import ExecutionStep, TaskMap

from typing import List
from spacy.matcher import Matcher

spacy.prefer_gpu()
nlp = spacy.load("en_core_web_sm")


class RequirementsAugmenter(AbstractSimpleStepAugmenter):

    def condition(self, step: ExecutionStep) -> bool:
        if len(step.response.screen.requirements) > 0:
            return False
        return True

    def get_transformed_input(self, task_map: TaskMap):
        requirements = task_map.requirement_list
        return requirements

    @staticmethod
    def __process_texts(texts: List[str]):
        processed_texts = list(nlp.pipe(texts))
        nouns_per_text_list = [set(
            chunk.root.lemma_.lower() for chunk in processed_text.noun_chunks if not chunk.root.pos_ == "PRON"
        ) for processed_text in processed_texts]

        return nouns_per_text_list

    @staticmethod
    def __format_requirements(requirement_node_list: List[RequirementNode]):
        # find and match patterns for requirements' amounts

        matcher = Matcher(nlp.vocab)

        pattern1 = [{'POS': 'NUM'}, {'POS': 'NUM', 'OP': '?'}, {'POS': 'NOUN'}]
        pattern2 = [{'POS': 'NUM'}, {'POS': 'NUM', 'OP': '?'}, {"ORTH": "-", 'OP': '?'}, {'POS': 'NOUN'}]
        pattern3 = [{'POS': 'NUM'}, {"TEXT": {"REGEX": "^\d+(?:/\d+)?-\w+$"}}]
        pattern4 = [{'POS': 'NUM'}, {'POS': 'NUM'}, {"TEXT": {"REGEX": "^\d+(?:/\d+)?-\w+$"}}]
        pattern5 = [{'POS': 'NUM'}]

        matcher.add("Amounts", [pattern1, pattern2, pattern3, pattern4, pattern5], greedy="LONGEST")

        for req in requirement_node_list:
            processed_texts = nlp(req.name)

            matches = matcher(processed_texts)
            spans = [processed_texts[start:end] for _, start, end in matches]

            if len(spans) > 0:
                req.amount = [span.text for span in spans][0]
                req.name = req.name.replace(str(req.amount) + ' ', '')

        return requirement_node_list

    def link_requirements_to_step(
            self, step_text: str, requirement_node_list: List[RequirementNode]) -> List[set[str]]:

        # process steps
        nouns_per_step_list = self.__process_texts([step_text])

        # format requirements
        requirement_node_list = self.__format_requirements(requirement_node_list)

        # process requirements
        requirements_texts = [requirement.name for requirement in requirement_node_list]
        nouns_per_requirement_list = self.__process_texts(requirements_texts)

        # one step can have multiple requirement matches
        step_requirement_match_list = []
        for step_noun_set in nouns_per_step_list:
            matched_requirement_nodes = set()
            for index, requirement_noun_set in enumerate(nouns_per_requirement_list):
                overlap = set(requirement_noun_set).intersection(set(step_noun_set))
                if overlap:
                    matched_requirement_nodes.add(requirement_node_list[index].name)

            step_requirement_match_list.append(matched_requirement_nodes)

        return step_requirement_match_list

    def apply_output(self, step: ExecutionStep, linked_requirements) -> ExecutionStep:

        screen = ScreenInteraction()

        screen.footer = step.response.screen.footer
        screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        for requirement in linked_requirements:
            for req in requirement:
                screen.requirements.append(str(req))

        step.response.screen.MergeFrom(screen)

        return step

    def process(self, step: OutputInteraction, requirements) -> OutputInteraction:
        step_text = step.response.screen.paragraphs[0]
        linked_requirements = self.link_requirements_to_step(step_text, requirements)
        return linked_requirements
