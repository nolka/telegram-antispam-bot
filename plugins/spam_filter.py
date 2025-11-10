import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

class SpamFilter:
    def __init__(self, spam_messages: list[str], normal_messages: list[str]):
        self.spam_messages = [x.lower() for x in spam_messages]
        self.normal_messages = [x.lower() for x in normal_messages]
        self.ml_model = None
        self.is_trained = False

        self._build_ml_model(spam_messages, normal_messages)

    def _build_ml_model(self, spam_messages: list[str], normal_messages: list[str]):
        messages = spam_messages + normal_messages
        labels = ['spam'] * len(spam_messages) + ['ham'] * len(normal_messages)

        self.ml_model = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('classifier', MultinomialNB())
        ])

        self.ml_model.fit(messages, labels)
        self.is_trained = True

    def add_spam_phrases(self, phrases):
        if isinstance(phrases, str):
            phrases = [phrases]

        for phrase in phrases:
            self.spam_messages.append(phrase.lower())

        self._build_ml_model(self.spam_messages, self.normal_messages)


    def is_spam(self, message: str):
        if not self.is_trained:
            return False

        result = self.ml_model.predict([message.lower()])
        prediction = result[0]

        return prediction == 'spam'
