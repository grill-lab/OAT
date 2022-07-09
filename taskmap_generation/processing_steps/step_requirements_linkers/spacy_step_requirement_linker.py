import sys
sys.path.insert(0, '/shared')
sys.path.insert(0, '/shared/compiled_protobufs')

from task_graph.nodes.requirement_node import RequirementNode

import spacy
from .abstract_step_requirement_linker import AbstractStepRequirementLinker
from typing import List, Tuple

spacy.prefer_gpu()
nlp = spacy.load("en_core_web_lg")

class SpacyStepRequirementLinker(AbstractStepRequirementLinker):
    """
    Uses spacy to link requirements steps. Drawback is that effectiveness is based on how well
    parses the step text.
    """

    def __process_texts(self, texts: List[str]):
        processed_texts = list(nlp.pipe(texts))
        nouns_per_text_list = [ set(
            chunk.root.lemma_.lower() for chunk in processed_text.noun_chunks if not chunk.root.pos_ == "PRON"
        ) for processed_text in processed_texts]

        return nouns_per_text_list

    def link_requirements_to_step(
        self, steps: List[Tuple[str, str, str]], requirement_node_list: List[RequirementNode]
    ) -> List[set]:
        
        # process steps
        step_texts = [step[0] for step in steps]
        nouns_per_step_list = self.__process_texts(step_texts)

        # process requirements
        requirements_texts = [requirement.name for requirement in requirement_node_list]
        nouns_per_requirement_list = self.__process_texts(requirements_texts)

        # one step can have multiple requirement matches
        step_requirement_match_list = []
        for step_noun_set in nouns_per_step_list:
            matched_requirement_nodes = set()
            for index, requirement_noun_set in enumerate(nouns_per_requirement_list):
                overlap = requirement_noun_set.intersection(step_noun_set)
                if overlap:
                    matched_requirement_nodes.add(requirement_node_list[index].node_id)
            step_requirement_match_list.append(matched_requirement_nodes)
        

        return step_requirement_match_list

