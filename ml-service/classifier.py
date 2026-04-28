"""
Category Classifier — Owner: Arpan Chatterjee
TF-IDF + Random Forest pipeline for receipt category classification.
"""

import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "classifier.pkl")
VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "models", "tfidf.pkl")


def train(X_train, y_train):
    """Placeholder for training pipeline."""
    pass


def predict(items_text: str, merchant: str = "") -> dict:
    """Returns a placeholder category and confidence."""
    # TODO: implement real prediction
    return {"category": "Supermarket / Grocery", "confidence": 0.0}
