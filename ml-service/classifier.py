"""
Category Classifier — Owner: Arpan Chatterjee
TF-IDF + Random Forest pipeline for receipt category classification.
Target: F1 > 0.80 on the CORD + SROIE + Indian receipts dataset.
"""

import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "classifier.pkl")
VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "models", "tfidf.pkl")


def train(X_train, y_train):
    """
    TODO (Arpan):
    1. Build a sklearn Pipeline: TfidfVectorizer → RandomForestClassifier
    2. Tune n_estimators, max_depth via GridSearchCV (cv=5, scoring='f1_weighted')
    3. Fit on X_train (items_text strings) and y_train (category labels)
    4. Save model and vectorizer with joblib.dump to models/
    5. Print classification_report on held-out validation set
    Expected categories: Groceries, Electronics, Clothing, Food & Dining,
                         Pharmacy, Fuel, Utilities, Other
    """
    # TODO: implement training pipeline
    raise NotImplementedError("train() not yet implemented — assigned to Arpan")


def predict(items_text: str, merchant: str = "") -> dict:
    """
    TODO (Arpan):
    1. Load saved vectorizer and model from models/ using joblib.load
    2. Combine items_text + merchant into a single feature string
    3. Transform with vectorizer, then call model.predict_proba
    4. Return top category and confidence score
    Returns: { "category": str, "confidence": float }
    """
    # TODO: implement prediction
    raise NotImplementedError("predict() not yet implemented — assigned to Arpan")
