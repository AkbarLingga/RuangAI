from __future__ import annotations

from collections.abc import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


LABELS = ("Negatif", "Netral", "Positif")


def create_sentiment_pipeline(
    random_state: int = 42, class_weight: str | None = None
) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=15_000,
                    strip_accents="unicode",
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight=class_weight,
                    max_iter=1_000,
                    random_state=random_state,
                ),
            ),
        ]
    )


def fit_sentiment_model(
    texts: Sequence[str],
    labels: Sequence[str],
    random_state: int = 42,
    class_weight: str | None = None,
) -> Pipeline:
    if len(texts) != len(labels) or len(texts) == 0:
        raise ValueError("Teks dan label harus tersedia dengan jumlah yang sama.")
    if set(labels) != set(LABELS):
        raise ValueError("Data latih harus memiliki label Negatif, Netral, dan Positif.")

    model = create_sentiment_pipeline(random_state, class_weight)
    model.fit(texts, labels)
    return model


def export_browser_model(model: Pipeline) -> dict[str, object]:
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["classifier"]
    return {
        "classes": classifier.classes_.tolist(),
        "vocabulary": {
            term: int(index) for term, index in vectorizer.vocabulary_.items()
        },
        "idf": [float(value) for value in vectorizer.idf_],
        "coefficients": [
            [float(value) for value in row] for row in classifier.coef_
        ],
        "intercepts": [float(value) for value in classifier.intercept_],
        "training_labels": "label otomatis leksikon",
    }


def predict_probabilities(model: Pipeline, text: str) -> dict[str, float]:
    probabilities = model.predict_proba([text])[0]
    classifier = model.named_steps["classifier"]
    return {
        label: float(probability)
        for label, probability in zip(classifier.classes_, probabilities)
    }
