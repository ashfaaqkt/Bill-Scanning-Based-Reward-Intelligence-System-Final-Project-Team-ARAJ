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
# POST { image_path } → calls Gemini AI, returns structured receipt JSON
@app.route("/ml/ocr", methods=["POST"])
def ocr_route():
    data = request.get_json() or {}
    image_path = data.get("image_path", "")
    if not image_path:
        return jsonify({"error": "image_path is required"}), 400

    result = ocr.extract_receipt_data(image_path)

    if result.get("error") == "unreadable":
        return jsonify(result), 422  # Image rejected due to blur or multi-bill

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
# POST { ocr_result, known_hashes? } → returns { fraud_score 0–1, signals dict }
# ocr_result is the Gemini OCR JSON (may contain error, reason, handwritten_flag fields)
@app.route("/ml/fraud-score", methods=["POST"])
def fraud_score_route():
    data = request.get_json() or {}
    ocr_result = data.get("ocr_result", {})
    known_hashes = data.get("known_hashes", [])
    result = fraud.score("", ocr_result, known_hashes)
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
