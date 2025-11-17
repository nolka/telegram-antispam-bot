import hashlib
import re
import string
from collections import defaultdict
from multiprocessing import Pool

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pymorphy3 import MorphAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

from logger import Logger
from storage import AbstractStorage

KIND_SPAM = 1
KIND_NORMAL = 0

COUNTER_BEFORE_LEARN_MAX = 5


class RussianTextPreprocessor:
    def __init__(self, use_stemming=True, use_lemmatization=True):
        self.use_stemming = use_stemming
        self.use_lemmatization = use_lemmatization
        self.morph = MorphAnalyzer()
        self.stop_words = set(stopwords.words("russian"))
        additional_stopwords = {
            "это",
            "как",
            "так",
            "и",
            "в",
            "над",
            "к",
            "до",
            "не",
            "на",
            "но",
            "за",
            "то",
            "с",
            "ли",
            "а",
            "во",
            "от",
            "со",
            "для",
            "о",
            "же",
            "ну",
            "вы",
            "бы",
            "что",
            "кто",
            "он",
            "она",
        }
        self.stop_words.update(additional_stopwords)

    def preprocess_text(self, text) -> str:
        text = text.lower()
        text = re.sub(f"[{re.escape(string.punctuation)}]", " ", text)
        text = re.sub(r"\d+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        tokens = word_tokenize(text, language="russian")

        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]

        if self.use_lemmatization and self.morph:
            tokens = [self.morph.parse(token)[0].normal_form for token in tokens]

        return " ".join(tokens)


class PredictionResult:
    __slots__ = ("is_spam", "possibility", "text")

    def __init__(self, prediction: bool, possibility: float, text: str):
        self.is_spam = prediction
        self.possibility = possibility
        self.text = text

    def __str__(self):
        return f"<PredictionResult: {self.is_spam}, {self.possibility:.2f}, {self.text}>"


class SpamMessageCollection:
    def __init__(self):
        self.message_map: dict[int, int] = defaultdict(int)

    def get_score(self, chat_id, message_id, user_id: int) -> int:
        return self.message_map[(chat_id, message_id, user_id)]

    def add_score(self, chat_id, message_id, user_id: int, value: int = 1) -> int:
        self.message_map[(chat_id, message_id, user_id)] += 1
        print(self.message_map)

        return self.get_score(chat_id, message_id, user_id)

    def has_item(self, chat_id, message_id, user_id: int) -> bool:
        return self.message_map.get((chat_id, message_id, user_id), None) is not None


class SpamFilter:
    def __init__(
        self,
        logger: Logger,
        storage: AbstractStorage,
        threshold: float = 0.6,
        worker_pool_size: int = 4,
    ):
        nltk.download("punkt")
        nltk.download("punkt_tab")
        nltk.download("stopwords")

        self._logger = logger
        self._storage: AbstractStorage = storage
        self._threshold = threshold
        self._preprocessor = RussianTextPreprocessor(use_stemming=True, use_lemmatization=True)
        self._vectorizer = TfidfVectorizer(
            max_features=10000,
            lowercase=True,
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
        )
        self._messages: dict[int, dict[str, list[str]]] = {
            KIND_SPAM: {},
            KIND_NORMAL: {},
        }
        self._worker_pool_size = worker_pool_size
        self._model: MultinomialNB = None
        self.is_trained: bool = False
        self.counter_before_learn: int = 0

        self.add_messages(KIND_SPAM, storage.get_spam_messages())
        self.add_messages(KIND_NORMAL, storage.get_normal_messages())

        self._build_ml_model()

    def _build_ml_model(self) -> None:
        self._logger.info("Rebuilding model")
        messages: list = list(self._messages[KIND_SPAM].values()) + list(
            self._messages[KIND_NORMAL].values()
        )

        labels = [KIND_SPAM] * len(self._messages[KIND_SPAM]) + [KIND_NORMAL] * len(
            self._messages[KIND_NORMAL]
        )

        self._logger.info("Processing messages...")
        processed_messages = []

        with Pool(self._worker_pool_size) as pool:
            result = pool.map(RussianTextPreprocessor().preprocess_text, messages)
            for i, msg in enumerate(result):
                processed_messages.append(msg)
                if i % 1000 == 0:
                    self._logger.info(f"Received processed: {i}/{len(messages)}")

        # Разделение данных на обучающую и тестовую выборки
        X_train, X_test, y_train, y_test = train_test_split(
            processed_messages,
            labels,
            test_size=0.2,
            random_state=42,
            stratify=labels,
        )

        self._logger.info(f"Size of training data: {len(X_train)}")
        self._logger.info(f"Size of test data: {len(X_test)}")

        self._logger.info("Vectorising texts...")
        X_train_tfidf = self._vectorizer.fit_transform(X_train)
        X_test_tfidf = self._vectorizer.transform(X_test)

        self._model = MultinomialNB(alpha=0.01)
        self._model.fit(X_train_tfidf, y_train)

        # Предсказание и оценка
        y_pred = self._model.predict(X_test_tfidf)

        self._logger.info(f"\n{'=' * 50}")
        self._logger.info("MODEL PERFORMANCE")
        self._logger.info(f"{'=' * 50}")
        self._logger.info(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        self._logger.info("\nClassification report:")
        self._logger.info(classification_report(y_test, y_pred))
        self._logger.info("\nErrors matrix:")
        self._logger.info(confusion_matrix(y_test, y_pred))

        self.is_trained = True

    def save(self) -> None:
        self._logger.info("Saving messages...")
        self._storage.save_spam_messages(self.get_messages(KIND_SPAM))
        self._storage.save_normal_messages(self.get_messages(KIND_NORMAL))

    def get_messages_dict(self, kind: int) -> dict[str, list[str]]:
        return self._messages[kind]

    def add_messages(self, kind: int, messages: list[str]) -> None:
        for msg in messages:
            normalized = self._normalize_text(msg)
            if not normalized:
                continue

            self._messages[kind][self._get_hash(normalized)] = normalized
            if self.counter_before_learn < COUNTER_BEFORE_LEARN_MAX:
                self.counter_before_learn += 1

    def get_messages(self, kind) -> list[str]:
        return self._messages[kind].values()

    def add_phrases(self, kind: int, phrases: list[str]) -> None:
        self.add_messages(kind, phrases)

        if kind == KIND_SPAM or self.counter_before_learn >= COUNTER_BEFORE_LEARN_MAX:
            self._build_ml_model()
            self.counter_before_learn = 0
            self.save()
            return

    def add_spam_phrase(self, phrase: str) -> None:
        key = self._get_hash(self._normalize_text(phrase))
        try:
            del self._messages[KIND_NORMAL][key]
        except KeyError as e:
            self._logger.error(f"Error deleting from normal messages: {e}")
        self.add_phrases(KIND_SPAM, [phrase])

    def del_spam_phrase(self, phrase: str) -> None:
        key = self._get_hash(self._normalize_text(phrase))
        try:
            del self._messages[KIND_SPAM][key]
        except KeyError as e:
            self._logger.error(f"Error deleting from spam: {e}")
        self.add_phrases(KIND_NORMAL, [phrase])
        self._build_ml_model()

    def is_spam(self, message: str) -> PredictionResult:
        if not self.is_trained:
            return PredictionResult(False, 0, "")

        processed_msg = self._preprocessor.preprocess_text(message)
        message_vec = self._vectorizer.transform([processed_msg])
        proba = self._model.predict_proba(message_vec)
        self._logger.info(f"Predict proba: {proba}")
        probability = self._model.predict_proba(message_vec)[0][1]
        kind_result = KIND_SPAM if probability > self._threshold else KIND_NORMAL

        return PredictionResult(
            kind_result == KIND_SPAM,
            probability,
            processed_msg,
        )

    def _normalize_text(self, text: str) -> str:
        return text.replace("\n", " ").strip().lower()

    def _get_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
