"""
Fraud Detection Pipeline — Owner: Ranjeet Singh
Multi-signal fraud scoring: OCR-flag analysis, perceptual hash dedup, CNN tamper check.
Status: OCR-based signals, pHash duplicate check, and CNN tamper check are all implemented.
"""

import os
from pathlib import Path


# MobileNetV2 trained at 448x448 by
#   train_fraud_cv.py --normalized --img-size 448
# under 5-fold grouped cross-validation on compression-normalized images:
# pooled out-of-fold AUC 0.805, and 0.864 on the 94 real photographs.
# The 448 input matters — at 224 a receipt is downscaled ~7x and an overwritten
# digit survives as only ~6 pixels. See report/fraud_test_report.md.
MODEL_PATH = Path(__file__).resolve().parent / "models" / "tamper_cnn_cv_normalized_448.pt"
IMG_SIZE = 448
PHASH_DISTANCE_THRESHOLD = 10

_tamper_model = None
_tamper_model_load_attempted = False


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
    pHash duplicate check and CNN tamper detection are active signals.
    """
    fraud_score, signals = calculate_fraud_score(ocr_result)

    if image_path:
        if check_phash_duplicate(image_path, known_hashes or []):
            fraud_score += 0.40
            signals["duplicate"] = True

        tamper_probability = check_tamper_cnn(image_path)
        if tamper_probability >= 0.50:
            fraud_score += 0.40
            signals["tamper"] = True

    return {
        "fraud_score": min(1.0, round(fraud_score, 4)),
        "signals": signals
    }


# ── DETECTOR IMPLEMENTATIONS (Notebook 03) ───────────────────
# pHash duplicate check and CNN tamper classifier — trained/validated in NB 03.

def check_phash_duplicate(image_path, known_hashes):
    """Perceptual hash duplicate check — compare image pHash against set of known hashes."""
    if not image_path or not known_hashes:
        return False

    try:
        from PIL import Image
        import imagehash
    except Exception:
        return False

    try:
        with Image.open(image_path) as img:
            current_hash = imagehash.phash(img)
    except Exception:
        return False

    for raw_hash in known_hashes:
        try:
            known_hash = imagehash.hex_to_hash(str(raw_hash))
        except Exception:
            continue
        if current_hash - known_hash <= PHASH_DISTANCE_THRESHOLD:
            return True

    return False

def _load_tamper_model(device):
    """Loads the CNN once per process — it is ~45 MB, too big to reload per receipt."""
    global _tamper_model, _tamper_model_load_attempted

    if _tamper_model_load_attempted:
        return _tamper_model
    _tamper_model_load_attempted = True

    try:
        import torch
        # weights_only defaults to True from PyTorch 2.6; this checkpoint is a full
        # nn.Module, so it must be opted out explicitly or loading raises and the
        # CNN silently falls back to the baseline for every receipt.
        _tamper_model = torch.load(MODEL_PATH, map_location=device, weights_only=False)
        if isinstance(_tamper_model, dict):
            # A state_dict was saved instead of the model — cannot infer from it.
            print("fraud.py: models/ holds a state_dict, not a full model — CNN disabled")
            _tamper_model = None
        else:
            _tamper_model.eval()
    except Exception as exc:
        print(f"fraud.py: tamper CNN failed to load ({exc}) — falling back to baseline")
        _tamper_model = None

    return _tamper_model


def check_tamper_cnn(image_path):
    """CNN tamper classifier — predicts probability that receipt has been digitally altered."""
    if not image_path or not os.path.exists(image_path):
        return 0.05

    if not MODEL_PATH.exists():
        # Model file missing (gitignored by design). Upload tamper_cnn_sprint2_auc076.pt from
        # Drive to ml-service/models/ to enable CNN inference; returns baseline until then.
        return 0.05

    try:
        import torch
        from torchvision import transforms
        from PIL import Image as PILImage
    except Exception:
        return 0.05

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = _load_tamper_model(device)
        if model is None:
            return 0.05

        # Must match the training resolution exactly — serving at 224 a model
        # trained at 448 silently degrades every prediction.
        transform = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        with PILImage.open(image_path) as img:
            tensor = transform(img.convert("RGB")).unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(tensor)
            if hasattr(output, "logits"):
                output = output.logits
            if output.shape[-1] == 1:
                probability = torch.sigmoid(output).item()
            else:
                probability = torch.softmax(output, dim=1)[0, 1].item()

        return float(max(0.0, min(1.0, probability)))
    except Exception:
        return 0.05
