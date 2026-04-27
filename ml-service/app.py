"""
ML Microservice — Team ARAJ
Flask entry point exposing all ML pipeline routes to the Node.js backend.
Run: python app.py  (default port 5001)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    """Health check — called by backend before every ML request."""
    return jsonify({"status": "ok"})


@app.route("/ml/classify", methods=["POST"])
def classify():
    """
    Owner: Arpan Chatterjee
    Input:  { "items_text": str, "merchant": str }
    Output: { "category": str, "confidence": float }
    TODO: import classifier.py and call classifier.predict(items_text, merchant)
    """
    data = request.get_json()
    # TODO: replace with real classifier
    return jsonify({"category": "Groceries", "confidence": 0.0, "status": "placeholder"})


@app.route("/ml/fraud-score", methods=["POST"])
def fraud_score():
    """
    Owner: Ranjeet Singh
    Input:  { "image_path": str, "metadata": { "total": float, ... } }
    Output: { "fraud_score": float, "signals": { "blur": bool, "duplicate": bool, "tamper": bool } }
    TODO: import fraud.py and call fraud.score(image_path, metadata)
    """
    data = request.get_json()
    # TODO: replace with real fraud pipeline
    return jsonify({
        "fraud_score": 0.0,
        "signals": {"blur": False, "duplicate": False, "tamper": False},
        "status": "placeholder"
    })


@app.route("/ml/anomaly", methods=["POST"])
def anomaly():
    """
    Owner: Ranjeet Singh
    Input:  { "user_id": str, "amount": float, "category": str, "date": str }
    Output: { "anomaly_score": float, "is_anomaly": bool }
    TODO: import anomaly.py and call anomaly.score(user_id, amount, category, date)
    """
    data = request.get_json()
    # TODO: replace with real anomaly detector
    return jsonify({"anomaly_score": 0.0, "is_anomaly": False, "status": "placeholder"})


@app.route("/ml/update-profile", methods=["POST"])
def update_profile():
    """
    Owner: Arpan Chatterjee
    Input:  { "user_id": str, "category": str, "amount": float, "merchant": str }
    Output: { "updated": bool }
    TODO: import user_profile.py and call user_profile.update(user_id, category, amount, merchant)
    """
    data = request.get_json()
    # TODO: replace with real profile update
    return jsonify({"updated": True, "status": "placeholder"})


@app.route("/ml/recommend", methods=["POST"])
def recommend():
    """
    Owner: Arpan Chatterjee
    Input:  { "user_id": str, "top_n": int }
    Output: { "recommendations": [ { "offer": str, "score": float }, ... ] }
    TODO: import recommend.py and call recommend.rank(user_id, top_n)
    """
    data = request.get_json()
    # TODO: replace with real reward ranker
    return jsonify({"recommendations": [], "status": "placeholder"})


if __name__ == "__main__":
    port = int(os.getenv("ML_PORT", 5001))
    app.run(debug=True, port=port)
