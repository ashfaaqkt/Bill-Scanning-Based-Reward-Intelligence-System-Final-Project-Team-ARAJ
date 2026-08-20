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

# Probability above which the CNN's verdict counts as a tamper signal.
#
# This was 0.50, chosen as the obvious midpoint rather than measured. At AUC
# 0.805 that midpoint is expensive: report/model_cards/fraud_cnn.md puts it at
# roughly 28% false positives on genuine receipts out-of-fold, so about one
# honest bill in three was carrying a tamper signal — enough that the signal
# stopped meaning anything.
#
# 0.82 is the operating point from the model card's table: 50.4% recall on
# tampered images for 9.2% false positives. Recall drops, and that is the
# deliberate half of the trade — a signal that fires on a third of genuine
# receipts is not worth the extra recall, because nobody can act on it.
#
# Changing this changes a documented result. Update the model card's operating
# point alongside it, or the report and the code will disagree.
TAMPER_THRESHOLD = 0.82

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

    # Gemini detected handwritten annotations on a printed receipt.
    #
    # This used to set signals["tamper"] as well. That was wrong twice over.
    # The client renders "tamper" as "the image shows signs of editing" and
    # "handwritten" as "handwriting detected on a printed bill", so one finding
    # was reported as two, and a real tampered bill came back reading as though
    # both the CNN and Gemini had fired when only Gemini had. It also meant
    # every handwritten receipt — the norm on small Indian bills — carried a
    # tamper signal the CNN never raised, which is what made the tamper warning
    # feel like it fired on everything.
    #
    # Handwriting has its own signal and its own weight. "tamper" now means
    # exactly one thing: the CNN cleared its threshold.
    if ocr_result.get("handwritten_flag"):
        base_score += 0.30
        signals["handwritten"] = True

    return min(1.0, base_score), signals  # Cap final score at 1.0


# ── MAIN ENTRY POINT ───────────────────────────────────────────
# Called by /ml/fraud-score; combines OCR signals into a single score + flags
def score(image_path, ocr_result, known_hashes=None):
    """
    Public API — returns fraud_score (0–1), a signals breakdown, the tamper
    probability, and the image's perceptual hash.

    `image_phash` is returned so the caller can STORE it. The duplicate check
    can only compare against hashes it is given, and until the backend persists
    one per receipt there is nothing to compare against — the signal was
    implemented and dead. See check_phash_duplicate().
    """
    fraud_score, signals = calculate_fraud_score(ocr_result)
    image_phash = None
    tamper_probability = None

    if image_path:
        # Hash once and reuse: the comparison and the value handed back to the
        # caller are the same number, and phash() decodes the whole image.
        image_phash = compute_phash(image_path)

        if is_duplicate_hash(image_phash, known_hashes or []):
            fraud_score += 0.40
            signals["duplicate"] = True

        tamper_probability = check_tamper_cnn(image_path)
        if tamper_probability >= TAMPER_THRESHOLD:
            fraud_score += 0.40
            signals["tamper"] = True

    return {
        "fraud_score": min(1.0, round(fraud_score, 4)),
        "signals": signals,
        # Surfaced so the client can show what the CNN actually said rather than
        # inferring it from the blended score.
        "tamper_probability": (round(tamper_probability, 4)
                               if tamper_probability is not None else None),
        "image_phash": image_phash,
    }


# ── DETECTOR IMPLEMENTATIONS (Notebook 03) ───────────────────
# pHash duplicate check and CNN tamper classifier — trained/validated in NB 03.

def compute_phash(image_path):
    """Perceptual hash of an image as a hex string, or None if it cannot be read."""
    if not image_path:
        return None
    try:
        from PIL import Image
        import imagehash
    except Exception:
        return None
    try:
        with Image.open(image_path) as img:
            return str(imagehash.phash(img))
    except Exception:
        return None


def is_duplicate_hash(current_hash, known_hashes):
    """
    True when `current_hash` is within PHASH_DISTANCE_THRESHOLD of any known one.

    This is a NEAR-duplicate test, which is the point: the SHA-256 fingerprint in
    the backend catches byte-identical resubmissions, but a receipt photographed
    a second time, cropped or re-compressed produces different bytes and different
    OCR text. Those still hash close together perceptually.
    """
    if not current_hash or not known_hashes:
        return False

    try:
        import imagehash
    except Exception:
        return False

    try:
        current = imagehash.hex_to_hash(str(current_hash))
    except Exception:
        return False

    for raw_hash in known_hashes:
        try:
            known = imagehash.hex_to_hash(str(raw_hash))
        except Exception:
            continue                      # skip a malformed stored hash
        if current - known <= PHASH_DISTANCE_THRESHOLD:
            return True

    return False


def check_phash_duplicate(image_path, known_hashes):
    """Back-compat wrapper — hashes the file, then compares. Used by test_fraud.py."""
    return is_duplicate_hash(compute_phash(image_path), known_hashes)

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
        # Model file missing (gitignored by design). Fetch the checkpoint named in
        # MODEL_PATH above into ml-service/models/ — see fetch_models.py — to enable
        # CNN inference; every receipt scores the baseline until then.
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
