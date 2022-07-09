from sklearn.feature_extraction._stop_words import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from models.domain_classification.abstract_model import AbstractDomainClassifier
import pandas as pd
import numpy as np
import pickle
import json
import os


def entropy(array, base=2.0):
    correction = np.array([1e-5] * 6)
    return -np.sum(array * np.log(array + correction) / np.log(base), axis=-1)


class DomainClassifier(AbstractDomainClassifier):

    def __init__(self, custom_stop_words=None):

        if custom_stop_words is None:
            custom_stop_words = []

        stop_words = list(ENGLISH_STOP_WORDS) + custom_stop_words

        self.tfidf = TfidfVectorizer(sublinear_tf=True,
                                     min_df=5,
                                     ngram_range=(1, 2),
                                     lowercase=True,
                                     stop_words=stop_words)
        self.model = MultinomialNB()
        self.id_to_domain = {}
        self.domain_list = []

    @staticmethod
    def load_data(path, balance=True, max_data=None):
        """ Read training and test data"""

        # Read data.
        dataframe = pd.read_csv(path)

        if 'title' in dataframe.columns:
            # fix for training dataframe
            dataframe = dataframe[dataframe.apply(lambda row: row['title'].isascii(), axis=1)]
            dataframe = dataframe.rename(columns={"title": "Utterance"})
            dataframe = dataframe[['Utterance', 'Domain']]


        # Balance data.
        if balance:
            lowest_domain_count = int(dataframe.groupby('Domain').count().min())

            print('balance training data with {} samples for each domain class'.format(lowest_domain_count))

            if (max_data is not None) and (max_data < lowest_domain_count):
                lowest_domain_count = max_data

            domain_dfs = [
                dataframe[dataframe['Domain'] == domain].sample(lowest_domain_count)
                for domain in list(dataframe['Domain'].unique())
            ]
            dataframe = pd.concat(domain_dfs)

        return dataframe

    def fit(self, train_df):
        """ Fit naive bayes model that uses tf-id tokenisation"""
        print('--- fitting model ---')
        train_df['domain_id'] = train_df['Domain'].factorize()[0]

        # Get category to ID map.
        category_id_df = train_df[['Domain', 'domain_id']].drop_duplicates().sort_values('domain_id')
        self.id_to_domain = dict(category_id_df[['domain_id', 'Domain']].values)
        
        # Ordered list of domains.
        self.domain_list = [self.id_to_domain[k] for k in sorted(self.id_to_domain.keys(), reverse=False)]

        # Build input data.
        X_train = self.tfidf.fit_transform(train_df['Utterance']).toarray()
        y_train = train_df['domain_id']
        print("X.shape: {}, y.shape: {}".format(X_train.shape, y_train.shape))

        # Train model.
        self.model.fit(X_train, y_train)

    def get_action(self, utterance):
        """ Get action based on domain classification results, ([DOMAIN], {CONFIDENCE}) """
        distribution = self.model.predict_proba(self.tfidf.transform([utterance]))
        idx = np.argmax(distribution)

        top_score = distribution[0, idx]
        top_domain = self.domain_list[idx]
        dist_entropy = entropy(distribution)

        if top_score >= 0.5:
            return top_domain, "high"

        elif dist_entropy > 2.0:
            return 'UndefinedDomain', "low"

        else:
            if top_domain in ['FinancialDomain', 'LegalDomain', 'MedicalDomain']:
                top_domain = 'UndefinedDomain'

            return top_domain, "low"

    def predict_test(self, utterences):
        """ Predict utterances (list of text) and predict a domain based on confidence score and thresholds. """
        pred_df = pd.DataFrame()
        pred_df['Utterance'] = utterences

        # Parse prediction to get domain and confidence.
        pred_df['pred'] = pred_df['Utterance'].apply(lambda x: self.get_action(x))

        pred_df['pred_Domain'] = pred_df.apply(lambda x: x['pred'][0], axis=1)
        pred_df['pred_confidence'] = pred_df.apply(lambda x: x['pred'][1], axis=1)
        return pred_df

    def predict(self, utterence):
        """ Return a dict domain classification confidences: {domain: confidence}. """
        outputs = self.model.predict_proba(self.tfidf.transform([utterence]))
        return {
            k: s for k, s in zip(self.domain_list, outputs[0])
        }

    def eval_testset(self, test_df, breakdown=True):
        """ Run evlautaion on a predefined testset"""
        print("="*20)

        pred_df = self.predict_test(utterences=test_df['Utterance'].values)
        test_df = test_df.merge(pred_df, left_index=True, right_index=True)

        # Add correct based on high confidence.
        test_df['correct_high'] = np.where(
            (test_df['Domain'] == test_df['pred_Domain']) & (test_df['pred_confidence'] == 'high'), 1.0, 0.0)
        # Add correct based on low confidence.
        test_df['correct_low'] = np.where(
            (test_df['Domain'] == test_df['pred_Domain']) & (test_df['pred_confidence'] == 'low'), 1.0, 0.0)
        test_df['total'] = 1.0

        def print_overall_stats(df, correct='correct_high'):
            print('overall score: {:.2f}, i.e. {} out of {}'.format(sum(df[correct]) / (sum(df['total']) or 1),
                                                                    sum(df[correct]),
                                                                    sum(df['total'])))
        def print_domain_stats(df, correct='correct_high'):
            for domain in self.domain_list:
                print('--- {} ---'.format(domain))
                print(' -> score: {:.2f}, {} out of {}'.format(
                    sum(df[df['Domain'] == domain][correct]) / (sum(df[df['Domain'] == domain]['total']) or 1),
                    sum(df[df['Domain'] == domain][correct]),
                    sum(df[df['Domain'] == domain]['total'])))

        conf_df = test_df[test_df['pred_confidence'] == "high"]
        correct = 'correct_high'
        print('--- High Confidence Results ---')
        print_overall_stats(conf_df, correct)
        if breakdown:
            print('\n*** DOMAIN ***')
            print_domain_stats(conf_df, correct)

        conf_df = test_df[test_df['pred_confidence'] == "low"]
        correct = 'correct_low'
        print('--- Low Confidence Results ---')
        print_overall_stats(conf_df, correct)
        if breakdown:
            print('\n*** DOMAIN ***')
            print_domain_stats(conf_df, correct)

    def save(self, path):
        """ Save model and """
        if not os.path.exists(path):
            os.mkdir(path)

        with open(os.path.join(path, "tfidf.pkl"), "wb+") as file:
            pickle.dump(self.tfidf, file)

        with open(os.path.join(path, "naive_bayes.pkl"), "wb+") as file:
            pickle.dump(self.model, file)

        with open(os.path.join(path, 'domain_list.json'), 'w') as file:
            json.dump(self.domain_list, file)

        with open(os.path.join(path, 'id_to_domain.json'), 'w') as file:
            json.dump(self.id_to_domain, file)

    def load(self, path):
        with open(os.path.join(path, "tfidf.pkl"), "rb") as file:
            self.tfidf = pickle.load(file)

        with open(os.path.join(path, "naive_bayes.pkl"), "rb") as file:
            self.model = pickle.load(file)

        with open(os.path.join(path, 'domain_list.json'), 'r') as file:
            self.domain_list = json.load(file)

        with open(os.path.join(path, 'id_to_domain.json'), 'r') as file:
            self.id_to_domain = json.load(file)






