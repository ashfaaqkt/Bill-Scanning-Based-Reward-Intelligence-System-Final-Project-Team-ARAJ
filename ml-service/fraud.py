"""
Fraud Detection Pipeline — Owner: Ranjeet Singh
Multi-signal fraud scoring: OCR-flag analysis, perceptual hash dedup, CNN tamper check.
Status: OCR-based signals are active; phash and CNN checks are stubs (see Notebook 03).
"""

import os


# ── SIGNAL EXTRACTION FROM OCR OUTPUT ─────────────────────────
# Reads Gemini OCR result JSON for built-in fraud flags
def calculate_fraud_score(ocr_result):
    """
    Derives fraud score from OCR flags.
    Adds weight per signal: multi-bill +0.5, blur +0.1, handwritten +0.3.
    Returns (score capped at 1.0, signals dict).
    """
    base_score = 0.05  # Every receipt starts with a low baseline (clean assumed)
    signals = {
        "blur": False,
        "duplicate": False,
        "tamper": False,
        "handwritten": False,
        "multi_bill": False
    }

    if not ocr_result:
        return base_score, signals

    # Multiple receipts in one photo — high fraud risk
    if ocr_result.get("error") == "multi_bill_detected":
        base_score += 0.50
        signals["multi_bill"] = True

    # Blurry image — may be hiding tampered text
    if ocr_result.get("reason") == "image_too_blurry":
        base_score += 0.10
        signals["blur"] = True

    # Gemini detected handwritten annotations on a printed receipt
    if ocr_result.get("handwritten_flag"):
        base_score += 0.30
        signals["handwritten"] = True
        signals["tamper"] = True

    return min(1.0, base_score), signals  # Cap final score at 1.0


# ── MAIN ENTRY POINT ───────────────────────────────────────────
# Called by /ml/fraud-score; combines OCR signals into a single score + flags
def score(image_path, ocr_result, known_hashes=None):
    """
    Public API — returns fraud_score (0–1) and a signals breakdown dict.
    phash duplicate check and CNN tamper detection are future additions.
    """
    fraud_score, signals = calculate_fraud_score(ocr_result)

    return {
        "fraud_score": fraud_score,
        "signals": signals
    }


# ── PLACEHOLDER DETECTORS (WIP — Ranjeet) ─────────────────────
# These will be wired in once Notebook 03 completes model training

def check_phash_duplicate(image_path, known_hashes):
    """Perceptual hash duplicate check — compare image pHash against set of known hashes."""
    return False  # TODO: imagehash.phash comparison

def check_tamper_cnn(image_path):
    """CNN tamper classifier — predicts probability that receipt has been digitally altered."""
    return 0.05  # TODO: load tamper_cnn.pt and run MobileNetV2 inference
