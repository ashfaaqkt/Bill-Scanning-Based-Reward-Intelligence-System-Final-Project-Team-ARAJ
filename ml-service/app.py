"""
ML Microservice — Team ARAJ
Flask entry point exposing all ML pipeline endpoints to the Node.js backend.
Run: python app.py  (default port 5001, override via ML_PORT env var)
"""

# ── IMPORTS ────────────────────────────────────────────────────
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Each module owns one ML pipeline component
import classifier   # Category prediction (TF-IDF + Random Forest)
import fraud        # Multi-signal fraud scorer
import anomaly      # Spending anomaly detection — Isolation Forest (stub)
import user_profile # User interest vector updater (stub)
import recommend    # Reward ranker — collaborative filter (stub)
import ocr          # Receipt data extractor — Gemini AI

load_dotenv()

# ── FLASK APP SETUP ────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the Node.js backend on port 3000


# ── HEALTH CHECK ───────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    """Ping — backend uses this to confirm ML service is alive before forwarding requests."""
    return jsonify({"status": "ok"})


# ── OCR ENDPOINT ───────────────────────────────────────────────
# POST { image, mimeType } (base64 from the backend) → calls Gemini AI, returns
# structured receipt JSON. Legacy { image_path } is still accepted for the CLI/tests.
@app.route("/ml/ocr", methods=["POST"])
def ocr_route():
    data = request.get_json() or {}
    image_b64 = data.get("image", "")
    mime_type = data.get("mimeType", "image/jpeg")
    image_path = data.get("image_path", "")

    if image_b64:
        result = ocr.extract_receipt_data_from_base64(image_b64, mime_type)
    elif image_path:
        result = ocr.extract_receipt_data(image_path)
    else:
        return jsonify({"error": "image (base64) or image_path is required"}), 400

    if result.get("error") in ("unreadable", "multi_bill_detected"):
        return jsonify(result), 422  # Image rejected due to blur or multiple receipts detected

    # Quota exhaustion is not a fault in the receipt — it is a per-minute cap on
    # the key. 429 lets the client say "wait a moment and retry" instead of
    # blaming the image, which is what the generic error path did.
    if result.get("error") == "RATE_LIMITED":
        return jsonify(result), 429

    return jsonify(result)


# ── CATEGORY CLASSIFIER ────────────────────────────────────────
# POST { items_text, merchant } → returns { category, confidence }
@app.route("/ml/classify", methods=["POST"])
def classify_route():
    data = request.get_json() or {}
    items_text = data.get("items_text", "")
    merchant = data.get("merchant", "")
    if not items_text and not merchant:
        return jsonify({"error": "items_text or merchant is required"}), 400
    result = classifier.predict(items_text, merchant)
    return jsonify(result)


# ── FRAUD SCORER ───────────────────────────────────────────────
# POST { ocr_result, image?, mimeType?, known_hashes? }
#   → returns { fraud_score 0–1, signals dict }
#
# ocr_result is the Gemini OCR JSON (may contain error, reason, handwritten_flag).
# `image` is the same base64 payload sent to /ml/ocr.
#
# The image matters: fraud.score() only runs the perceptual-hash duplicate check
# and the 448px tamper CNN when it is given a path. This route previously passed
# an empty string, so both signals were skipped on every request and the live
# fraud score was OCR rule signals alone — the trained CNN never saw an upload.
@app.route("/ml/fraud-score", methods=["POST"])
def fraud_score_route():
    data = request.get_json() or {}
    ocr_result = data.get("ocr_result", {})
    known_hashes = data.get("known_hashes", [])
    image_b64 = data.get("image")
    mime_type = data.get("mimeType", "")

    # No image: still a valid request — score on OCR signals alone rather than
    # failing, which is what the backend falls back to if the upload is text-only.
    if not image_b64:
        return jsonify(fraud.score("", ocr_result, known_hashes))

    import base64
    import tempfile

    suffix = ocr._MIME_SUFFIX.get((mime_type or "").lower().strip(), ".jpg")
    tmp_path = None
    try:
        image_bytes = base64.b64decode(image_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        result = fraud.score(tmp_path, ocr_result, known_hashes)
    except Exception as exc:
        # A decode or scoring failure must not fail the upload; fall back to the
        # OCR-signal score and say so in the log.
        print(f"[WARN] fraud-score image path failed ({exc}) — OCR signals only")
        result = fraud.score("", ocr_result, known_hashes)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as exc:
                print(f"[WARN] Could not remove temp fraud file {tmp_path}: {exc}")

    return jsonify(result)


# ── ANOMALY DETECTION ──────────────────────────────────────────
# POST { user_id, amount, category, date } → returns { anomaly_score, is_anomaly }
@app.route("/ml/anomaly", methods=["POST"])
def anomaly_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    amount = data.get("amount", 0.0)
    category = data.get("category", "")
    date = data.get("date", "")
    result = anomaly.score(user_id, amount, category, date)
    return jsonify(result)


# ── USER PROFILE UPDATE ────────────────────────────────────────
# POST { user_id, category, amount, merchant } → updates spend interest vector
# Called asynchronously (fire-and-forget) after every receipt upload
@app.route("/ml/update-profile", methods=["POST"])
def update_profile_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    category = data.get("category", "")
    amount = data.get("amount", 0.0)
    merchant = data.get("merchant", "")
    result = user_profile.update(user_id, category, amount, merchant)
    return jsonify(result)


# ── REWARD RECOMMENDATIONS ─────────────────────────────────────
# POST { user_id, top_n } → returns ranked list of personalised reward offers
@app.route("/ml/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    top_n = data.get("top_n", 5)
    result = recommend.rank(user_id, top_n)
    return jsonify(result)


# ── SERVER START ───────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("ML_PORT", 5001))
    app.run(debug=True, port=port)
