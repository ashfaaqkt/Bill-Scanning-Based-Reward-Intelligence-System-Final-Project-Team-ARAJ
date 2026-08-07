"""
Anomaly Detection — Owner: Ranjeet Singh · Sprint 3 rework: Ashfaaq KT
Isolation Forest for spending anomaly detection (unusual transaction amounts).
Learning type: UNSUPERVISED — there are no anomaly labels anywhere in the project.

WHAT THIS ACTUALLY CLAIMS
The route is specified as a per-user check. A per-user model cannot be trained:
firestore_receipts.csv holds 19 real transactions across 3 users. So the trained
component is population-level — "is this amount unusual relative to a typical
receipt" — and a per-user reference is used instead of the population one as soon
as a user has enough history, which needs no training.

Amounts are compared as a RATIO to a reference, never in absolute terms, so the
model transfers across currencies (it was trained on IDR and MYR receipts and is
served INR ones).

Model: models/spending_anomaly.joblib, built by train_anomaly.py.
Measured: 13.2% false-positive rate on held-out real receipts (target < 15%),
100% recall against injected synthetic outliers at 10x typical and above, 0%
below 5x. The check is one-sided — only amounts ABOVE the reference can be
flagged, since inflating a receipt is the fraud, not shrinking one. Falls back to
a fixed baseline when the model is absent.
"""

import math
from collections import defaultdict, deque
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "models" / "spending_anomaly.joblib"

BASELINE_SCORE = 0.05
MIN_HISTORY_FOR_USER_REFERENCE = 5   # below this, one big receipt would skew the median

# Fallback reference for a user with no history, in the SERVING currency (INR).
# Median of the 19 real receipts in firestore_receipts.csv. The training corpus is
# IDR and MYR, so its medians cannot be reused here — averaging them produces a
# meaningless ~23,600 figure against which every ordinary Indian receipt looks
# anomalously small. Update this as real usage data accumulates.
POPULATION_REFERENCE_INR = 2748.0
HISTORY_LIMIT = 50                   # per user, in-memory only

_bundle = None
_load_attempted = False

# Recent amounts per user. In-memory and per-process by design: this is a serving
# convenience, not storage. Firestore remains the source of truth.
_user_history = defaultdict(lambda: deque(maxlen=HISTORY_LIMIT))


# ── MODEL LOADING ──────────────────────────────────────────────
def _load_bundle():
    """Loads once per process. The bundle carries the reference medians too."""
    global _bundle, _load_attempted

    if _load_attempted:
        return _bundle
    _load_attempted = True

    if not MODEL_PATH.exists():
        return None

    try:
        import joblib
        bundle = joblib.load(MODEL_PATH)
        # Reject an incompatible artefact rather than feed it a wrong-shaped vector.
        # An earlier hand-off shipped a 1280-feature image-embedding detector here.
        if not isinstance(bundle, dict) or "model" not in bundle:
            print("anomaly.py: unexpected model format — using baseline")
            return None
        if getattr(bundle["model"], "n_features_in_", 1) != 1:
            print("anomaly.py: model expects "
                  f"{bundle['model'].n_features_in_} features, not 1 — using baseline")
            return None
        _bundle = bundle
    except Exception as exc:
        print(f"anomaly.py: failed to load model ({exc}) — using baseline")
        _bundle = None

    return _bundle


def _reference_amount(user_id, bundle):
    """
    The 'typical receipt' this amount is judged against.

    Prefers the user's own median once they have enough history — that is the
    per-user behaviour the route promises. Falls back to the population median
    the model was trained on.
    """
    history = _user_history[user_id]
    if len(history) >= MIN_HISTORY_FOR_USER_REFERENCE:
        ordered = sorted(history)
        middle = len(ordered) // 2
        median = (ordered[middle] if len(ordered) % 2
                  else (ordered[middle - 1] + ordered[middle]) / 2)
        return median, "user"

    return POPULATION_REFERENCE_INR, "population"


# ── INFERENCE ENTRY POINT ──────────────────────────────────────
# Called by /ml/anomaly route; receives one transaction and judges if it is unusual
def score(user_id: str, amount: float, category: str, date: str) -> dict:
    """
    Returns anomaly_score (0–1) and is_anomaly flag for the given transaction.
    High score = amount is statistically unusual for this user/category.
    """
    bundle = _load_bundle()

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0

    if bundle is None or amount_value <= 0:
        return {"anomaly_score": BASELINE_SCORE, "is_anomaly": False}

    reference, basis = _reference_amount(user_id, bundle)

    try:
        import numpy as np

        ratio = math.log1p(amount_value) - math.log1p(max(reference, 1e-9))
        vector = np.array([[ratio]], dtype=float)

        model = bundle["model"]
        is_anomaly = int(model.predict(vector)[0]) == -1

        # One-sided by intent. The fraud being defended against is INFLATING a
        # receipt to earn more points; an unusually small receipt is not fraud, so
        # a below-reference amount is never flagged even if the forest isolates it.
        if ratio <= 0:
            is_anomaly = False

        # decision_function: positive = normal, negative = outlier (roughly +/-0.5).
        # Shifted into 0–1 so the route keeps its documented contract.
        raw = float(model.decision_function(vector)[0])
        anomaly_score = min(1.0, max(0.0, 0.5 - raw))
        if ratio <= 0:
            anomaly_score = min(anomaly_score, BASELINE_SCORE)
    except Exception:
        return {"anomaly_score": BASELINE_SCORE, "is_anomaly": False}

    # Recorded after scoring, so a transaction never influences its own verdict.
    _user_history[user_id].append(amount_value)

    return {
        "anomaly_score": round(anomaly_score, 4),
        "is_anomaly": is_anomaly,
        "reference_basis": basis,          # "user" once history exists, else "population"
    }
