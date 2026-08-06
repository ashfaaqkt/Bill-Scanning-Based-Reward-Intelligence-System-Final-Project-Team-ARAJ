"""
Anomaly Detection — Owner: Ranjeet Singh
Isolation Forest for spending anomaly detection (unusual transaction amounts).
Status: live when the trained model is present, baseline fallback when it is not.

The model binary (models/anomaly_detector.joblib) is gitignored — download it from
the team Drive into ml-service/models/ to enable real inference. Without it every
call returns the baseline score, which is what /api/upload already assumes.
"""

from datetime import datetime
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parent / "models" / "anomaly_detector.joblib"

# Returned when the model is missing/unusable — matches server.js's own default.
BASELINE_SCORE = 0.05

# Category → numeric code, using the three labels the OCR prompt emits.
CATEGORY_CODES = {"grocery": 0, "food": 1, "retail": 2}

_model = None
_model_load_attempted = False


# ── MODEL LOADING ──────────────────────────────────────────────
# Loaded once per process — the Flask worker serves many receipts.
def _load_model():
    global _model, _model_load_attempted

    if _model_load_attempted:
        return _model
    _model_load_attempted = True

    if not MODEL_PATH.exists():
        return None

    try:
        import joblib
        _model = joblib.load(MODEL_PATH)
    except Exception:
        _model = None

    return _model


# ── FEATURE BUILDING ───────────────────────────────────────────
def _category_code(category):
    """Maps an OCR/classifier category string onto the training code."""
    text = str(category or "").strip().lower()
    for keyword, code in CATEGORY_CODES.items():
        if keyword in text:
            return code
    return len(CATEGORY_CODES)  # unknown category bucket


def _build_features(amount, category, date):
    """
    Feature vector for the Isolation Forest: [amount, category, day, weekday].
    Order must match the training script — see the header note.
    """
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0

    day, weekday = 1, 0
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(str(date).strip(), date_format)
            day, weekday = parsed.day, parsed.weekday()
            break
        except (TypeError, ValueError):
            continue

    return [amount_value, _category_code(category), day, weekday]


# ── INFERENCE ENTRY POINT ──────────────────────────────────────
# Called by /ml/anomaly route; receives one transaction and judges if it is unusual
def score(user_id: str, amount: float, category: str, date: str) -> dict:
    """
    Returns anomaly_score (0–1) and is_anomaly flag for the given transaction.
    High score = amount is statistically unusual for this user/category.
    """
    model = _load_model()
    if model is None:
        return {"anomaly_score": BASELINE_SCORE, "is_anomaly": False}

    features = _build_features(amount, category, date)

    # The model was trained outside this repo, so refuse to guess on a shape
    # mismatch rather than feed it a wrongly ordered vector.
    expected = getattr(model, "n_features_in_", len(features))
    if expected != len(features):
        return {"anomaly_score": BASELINE_SCORE, "is_anomaly": False}

    try:
        import numpy as np
        vector = np.array(features, dtype=float).reshape(1, -1)

        # decision_function: positive = inlier, negative = outlier (roughly ±0.5).
        # Shift into a 0–1 score so the route keeps its documented contract.
        raw = float(model.decision_function(vector)[0])
        anomaly_score = min(1.0, max(0.0, 0.5 - raw))
        is_anomaly = int(model.predict(vector)[0]) == -1
    except Exception:
        return {"anomaly_score": BASELINE_SCORE, "is_anomaly": False}

    return {"anomaly_score": round(anomaly_score, 4), "is_anomaly": is_anomaly}
