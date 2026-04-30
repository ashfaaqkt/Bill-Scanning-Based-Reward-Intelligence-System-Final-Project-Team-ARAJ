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
    """Classify receipt text into a spend category."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
        return {"category": "Unknown", "confidence": 0.0, "model_ready": False}

    try:
        vectorizer = joblib.load(VECTORIZER_PATH)
        model = joblib.load(MODEL_PATH)
        text = f"{merchant} {items_text}".strip()
        vec = vectorizer.transform([text])
        category = model.predict(vec)[0]
        confidence = float(model.predict_proba(vec).max())
        return {"category": category, "confidence": round(confidence, 4), "model_ready": True}
    except Exception as exc:
        return {"category": "Unknown", "confidence": 0.0, "model_ready": False, "error": str(exc)}
