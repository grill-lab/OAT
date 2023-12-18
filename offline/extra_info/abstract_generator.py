from abc import ABC, abstractmethod
from purgo_malum import client

import spacy
spacy.prefer_gpu()
nlp = spacy.load("en_core_web_sm")
from spacy.matcher import Matcher
from spacy.util import filter_spans

class AbstractGenerator(ABC):
    
    @abstractmethod
    def add_initial_corpus(self) -> None:
        pass

    def filter_joke(self, joke):
        filtered_joke = client.contains_profanity(joke)
        if filtered_joke==True:
            return
        return joke
    
    def get_keywords(self, text:str):
        keywords = set()
        doc = nlp(text.lower())
        pattern1 = [{'POS': 'VERB' }, {'POS': 'NOUN' }]
        pattern2 = [{'POS': 'ADJ' }, {'POS': 'NOUN' }]

        matcher = Matcher(nlp.vocab)
        matcher.add("Noun patterns", [pattern1, pattern2])

        matches = matcher(doc)
        spans = [doc[start:end] for _, start, end in matches]
        for x in filter_spans(spans):
            keywords.add(str(x))

        for token in doc:
            if(token.pos_ == 'NOUN'):
                keywords.add(token.lemma_)
                    
        return keywords