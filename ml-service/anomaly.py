"""
Anomaly Detection — Owner: Ranjeet Singh
Isolation Forest for detecting unusual spending patterns per user.
"""

import os


def extract_features(user_id: str, amount: float, category: str, date: str) -> list:
    """
    TODO (Ranjeet):
    1. Load user's past transaction history from Firestore (or a local cache CSV)
    2. Build a feature vector:
       - amount (normalised by user's average)
       - day of week (0–6)
       - hour of day (0–23)
       - category frequency ratio (how often user shops this category)
       - merchant frequency ratio
    3. Return as a list of floats for the Isolation Forest
    """
    # TODO: implement feature extraction
    raise NotImplementedError("extract_features() not yet implemented — assigned to Ranjeet")


def score(user_id: str, amount: float, category: str, date: str) -> dict:
    """
    TODO (Ranjeet):
    1. Call extract_features() to build the feature vector
    2. Load the trained IsolationForest model from models/anomaly.pkl
    3. Call model.decision_function() — more negative = more anomalous
    4. Normalise to a 0–1 anomaly score (higher = more anomalous)
    5. Return score and boolean flag
    Returns: { "anomaly_score": float, "is_anomaly": bool }
    Note: train the model per-user on their own history (see notebook 02)
    """
    # TODO: implement anomaly scoring
    raise NotImplementedError("score() not yet implemented — assigned to Ranjeet")
