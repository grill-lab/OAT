from utils import get_file_system, logger
from typing import List
import os
import spacy
nlp = spacy.load("en_core_web_sm")

class FindCookingMethodsV0:

    WORDLIST_PATH = 'action_method_classifier/filter_utils/wordlist_v1.txt'

    def __init__(self):
        with open(self.WORDLIST_PATH, 'r') as f:
            self.word_list = []
            for line in f:
                self.word_list.append(line.strip().lower())
    
    # extract actions
    def __extract_actions(self, query):
        actions = []

        for token in query:
            if token.pos_ == "VERB":
                # there can only be one direct object child
                children = [child for child in token.children if child.dep_ == "dobj"]
                if children:
                    actions.append(query[token.i:children[0].i + 1])
        
        return actions

    def pred(self, action_step: str) -> List:
        processed_step = nlp(action_step)
        extracted_actions = self.__extract_actions(processed_step)
        logger.info(f"Actions extracted from step: {extracted_actions}")
        filtered_actions = []

        for action in extracted_actions:
            if any(word in action.text.lower() for word in self.word_list):
                filtered_actions.append(action.text)

        logger.info(f"Filtered actions: {filtered_actions}")
        return filtered_actions
