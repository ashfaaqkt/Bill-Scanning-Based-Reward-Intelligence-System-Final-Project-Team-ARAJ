"""
Fraud Detection Pipeline — Owner: Ranjeet Singh
Multi-signal fraud scoring: blur detection, perceptual hash deduplication,
and CNN-based tamper detection.
"""

import os


def check_blur(image_path: str) -> bool:
    """
    TODO (Ranjeet):
    1. Load image with OpenCV (cv2.imread)
    2. Convert to grayscale
    3. Compute Laplacian variance (cv2.Laplacian + .var())
    4. Return True (blurry) if variance < threshold (start with 100.0)
    5. Log the variance value for threshold tuning
    """
    # TODO: implement blur detection
    raise NotImplementedError("check_blur() not yet implemented — assigned to Ranjeet")


def check_phash_duplicate(image_path: str, known_hashes: list) -> bool:
    """
    TODO (Ranjeet):
    1. Load image with Pillow
    2. Compute perceptual hash with imagehash.phash()
    3. Compare against known_hashes list (Hamming distance < 10 = duplicate)
    4. Return True if a near-duplicate is found
    5. Store new hash in Firestore for future comparisons
    """
    # TODO: implement perceptual hash duplicate check
    raise NotImplementedError("check_phash_duplicate() not yet implemented — assigned to Ranjeet")


def check_tamper_cnn(image_path: str) -> float:
    """
    TODO (Ranjeet):
    1. Load a pretrained binary CNN from models/tamper_cnn.pt (genuine vs tampered)
    2. Preprocess image: resize to 224x224, normalize
    3. Run inference and return tamper probability (0.0–1.0)
    4. Train on dataset/genuine/ vs dataset/tampered/ — see notebook 03
    """
    # TODO: implement CNN tamper check
    raise NotImplementedError("check_tamper_cnn() not yet implemented — assigned to Ranjeet")


def score(image_path: str, metadata: dict, known_hashes: list = None) -> dict:
    """
    TODO (Ranjeet):
    1. Run check_blur, check_phash_duplicate, check_tamper_cnn
    2. Combine signals into a weighted fraud score (0.0–1.0)
       Suggested weights: blur=0.2, duplicate=0.4, tamper=0.4
    3. Return full signals dict + final score
    Returns: { "fraud_score": float, "signals": { "blur": bool, "duplicate": bool, "tamper": bool } }
    """
    # TODO: implement combined fraud scoring
    raise NotImplementedError("score() not yet implemented — assigned to Ranjeet")
