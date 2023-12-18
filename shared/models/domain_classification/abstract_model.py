
from abc import ABC, abstractmethod

class AbstractDomainClassifier(ABC):

    @abstractmethod
    def fit(self, train_df):
        pass

    @abstractmethod
    def eval_testset(self, test_df):
        pass

    @abstractmethod
    def predict(self, utterance):
        pass

    @abstractmethod
    def save(self, dir_path):
        pass

    @abstractmethod
    def load(self, dir_path):
        pass