"""
Anomaly Detection — Owner: Ranjeet Singh
Isolation Forest for spending anomaly detection (unusual transaction amounts).
Status: placeholder — returns static score until model is trained (see Notebook 03).
"""


# ── INFERENCE ENTRY POINT ──────────────────────────────────────
# Called by /ml/anomaly route; receives one transaction and judges if it is unusual
def score(user_id: str, amount: float, category: str, date: str) -> dict:
    """
    Returns anomaly_score (0–1) and is_anomaly flag for the given transaction.
    High score = amount is statistically unusual for this user/category.
    """
    return {"anomaly_score": 0.05, "is_anomaly": False}  # TODO: Isolation Forest inference
