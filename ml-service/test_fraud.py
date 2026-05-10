"""
Fraud Scoring Unit Tests — Owner: Ranjeet Singh
Validates calculate_fraud_score() against known OCR result scenarios.
Run: python test_fraud.py
"""

import fraud

# ── TEST SUITE ─────────────────────────────────────────────────
def test_fraud_scoring():
    print("Testing Fraud Scoring Logic...")

    # Case 1: Clean receipt — baseline score only (0.05)
    res1, signals1 = fraud.calculate_fraud_score({})
    print(f"Normal bill: score={res1}, signals={signals1}")
    assert round(res1, 2) == 0.05
    assert not any(signals1.values())

    # Case 2: Multiple receipts in one photo → +0.50 (high risk)
    res2, signals2 = fraud.calculate_fraud_score({"error": "multi_bill_detected"})
    print(f"Multi-bill: score={res2}, signals={signals2}")
    assert round(res2, 2) == 0.55
    assert signals2["multi_bill"] is True

    # Case 3: Blurry image → +0.10 (may be hiding tampered text)
    res3, signals3 = fraud.calculate_fraud_score({"reason": "image_too_blurry"})
    print(f"Blurry image: score={res3}, signals={signals3}")
    assert round(res3, 2) == 0.15
    assert signals3["blur"] is True

    # Case 4: Handwritten modification detected by Gemini → +0.30
    res4, signals4 = fraud.calculate_fraud_score({"handwritten_flag": True})
    print(f"Handwritten: score={res4}, signals={signals4}")
    assert round(res4, 2) == 0.35
    assert signals4["handwritten"] is True
    assert signals4["tamper"] is True

    # Case 5: Combined flags (multi-bill + handwritten) → capped at 0.85
    res5, signals5 = fraud.calculate_fraud_score({
        "error": "multi_bill_detected",
        "handwritten_flag": True
    })
    print(f"Combined: score={res5}, signals={signals5}")
    assert round(res5, 2) == 0.85
    assert signals5["multi_bill"] is True
    assert signals5["handwritten"] is True

    print("All fraud scoring tests passed!")

if __name__ == "__main__":
    test_fraud_scoring()
