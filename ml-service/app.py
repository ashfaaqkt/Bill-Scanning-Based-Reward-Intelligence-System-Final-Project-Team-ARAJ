"""
ML Microservice — Team ARAJ
Flask entry point exposing all ML pipeline routes to the Node.js backend.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Import modules
import classifier
import fraud
import anomaly
import user_profile
import recommend
import ocr

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "ok"})


@app.route("/ml/ocr", methods=["POST"])
def ocr_route():
    data = request.get_json() or {}
    image_path = data.get("image_path", "")
    if not image_path:
        return jsonify({"error": "image_path is required"}), 400
    
    result = ocr.extract_receipt_data(image_path)

    if result.get("error") == "unreadable":
        return jsonify(result), 422

    return jsonify(result)


@app.route("/ml/classify", methods=["POST"])
def classify_route():
    data = request.get_json() or {}
    items_text = data.get("items_text", "")
    merchant = data.get("merchant", "")
    result = classifier.predict(items_text, merchant)
    return jsonify(result)


@app.route("/ml/fraud-score", methods=["POST"])
def fraud_score_route():
    data = request.get_json() or {}
    image_path = data.get("image_path", "")
    metadata = data.get("metadata", {})
    result = fraud.score(image_path, metadata)
    return jsonify(result)


@app.route("/ml/anomaly", methods=["POST"])
def anomaly_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    amount = data.get("amount", 0.0)
    category = data.get("category", "")
    date = data.get("date", "")
    result = anomaly.score(user_id, amount, category, date)
    return jsonify(result)


@app.route("/ml/update-profile", methods=["POST"])
def update_profile_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    category = data.get("category", "")
    amount = data.get("amount", 0.0)
    merchant = data.get("merchant", "")
    result = user_profile.update(user_id, category, amount, merchant)
    return jsonify(result)


@app.route("/ml/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    top_n = data.get("top_n", 5)
    result = recommend.rank(user_id, top_n)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.getenv("ML_PORT", 5001))
    app.run(debug=True, port=port)
