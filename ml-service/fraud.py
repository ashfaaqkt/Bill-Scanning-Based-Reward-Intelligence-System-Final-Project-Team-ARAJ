"""
Fraud Detection Pipeline — Owner: Ranjeet Singh
Multi-signal fraud scoring: blur detection, perceptual hash deduplication,
and CNN-based tamper detection.
"""

import os


def check_blur(image_path: str) -> bool:
    """Placeholder for blur detection."""
    return False


def check_phash_duplicate(image_path: str, known_hashes: list) -> bool:
    """Placeholder for duplicate check."""
    return False


def check_tamper_cnn(image_path: str) -> float:
    """Placeholder for CNN tamper check."""
    return 0.05


def score(image_path: str, metadata: dict, known_hashes: list = None) -> dict:
    """Composite fraud score from blur, duplicate, and tamper signals."""
    known_hashes = known_hashes or []

    is_blurry = check_blur(image_path)
    is_duplicate = check_phash_duplicate(image_path, known_hashes)
    tamper_prob = check_tamper_cnn(image_path)

    # Weighted composite score; weights will be tuned once real detectors land
    fraud_score = round(
        0.3 * float(is_blurry)
        + 0.4 * float(is_duplicate)
        + 0.3 * tamper_prob,
        4,
    )

    return {
        "fraud_score": fraud_score,
        "signals": {
            "blur": is_blurry,
            "duplicate": is_duplicate,
            "tamper": tamper_prob > 0.5,
        },
    }
