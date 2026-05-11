"""
OCR Module — Team ARAJ (Ashfaaq Feroz)
Extracts structured receipt data from images using Google Gemini AI.
Pipeline: blur check → rate-limit gate → Gemini model fallback chain → JSON parse.
"""

import os
import json
import time
import cv2
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# ── ENVIRONMENT SETUP ──────────────────────────────────────────
# Load .env from ml-service/ so GEMINI_API_KEY is available
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Configure Gemini client with API key from .env
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# ── RATE LIMIT STATE ───────────────────────────────────────────
# Tracks last Gemini call time; enforces 23s gap to stay within 5 RPM free tier
last_request_time = 0
RATE_LIMIT_INTERVAL = 23  # 22s gap + 1s safety buffer

# ── BLUR DETECTION THRESHOLD ───────────────────────────────────
# Laplacian variance below this value → image too blurry to extract reliably
BLUR_THRESHOLD = 100

# ── GEMINI EXTRACTION PROMPT ───────────────────────────────────
# Instructs Gemini to detect multi-bill, blur, handwriting, and extract structured JSON
RECEIPT_PROMPT = (
    "Analyze this image carefully. "
    "1. Detect the number of receipts. If there is more than one receipt in the image, return exactly: {\"error\": \"multi_bill_detected\"}. "
    "2. Check for any handwritten modifications (e.g., changes to price, date, or merchant name). "
    "3. If the image is blurry or unreadable, return exactly: {\"error\": \"unreadable\"}. "
    "4. Otherwise, extract the following details into a strict JSON format: "
    "{"
    "\"rawMerchant\": \"string\", "
    "\"date\": \"string (YYYY-MM-DD)\", "
    "\"total\": number, "
    "\"category\": \"string ('Supermarket / Grocery', 'Food & Beverage', or 'General Retail')\", "
    "\"items\": [{ \"name\": \"string\", \"price\": number }], "
    "\"handwritten_flag\": boolean, "
    "\"handwritten_details\": \"string or null\""
    "}"
)

# ── HANDWRITING DENSITY ANOMALY DETECTOR ──────────────────────
# Printed receipts have roughly uniform text density across horizontal bands.
# A localised spike (e.g. a hand-scrawled price change) shows up as an outlier band.
def _detect_density_anomaly(image_path):
    """
    Splits image into 10 horizontal bands, computes dark-pixel density per band.
    Returns (anomaly_detected: bool, confidence: float 0–1).
    Confidence is 0 if no outlier band exceeds 3× the mean density.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        h, w = thresh.shape
        band_h = max(1, h // 10)
        densities = []
        for i in range(10):
            band = thresh[i * band_h: (i + 1) * band_h, :]
            densities.append(band.sum() / (band.size * 255))

        avg = sum(densities) / len(densities) if densities else 0
        if avg == 0:
            return False, 0.0

        outliers = [d for d in densities if d > avg * 3.0 and d > 0.15]
        if not outliers:
            return False, 0.0

        # Map outlier ratio to 0–1 confidence: 3× avg → 0, 10× avg → 1
        max_ratio = max(outliers) / avg
        confidence = round(min(1.0, (max_ratio - 3.0) / 7.0), 2)
        return True, confidence

    except Exception as e:
        print(f"[WARN] Density anomaly check failed: {e}")
        return False, 0.0


# ── MAIN EXTRACTION FUNCTION ───────────────────────────────────
def extract_receipt_data(image_path):
    """
    Full pipeline: blur check → rate-limit wait → Gemini call → JSON parse.
    Returns structured dict or an error dict (unreadable / TERMINAL_FAILURE / etc.).
    """
    global last_request_time

    if not api_key:
        return {"error": "GEMINI_API_KEY_MISSING"}

    # STEP 1 — Blur detection via OpenCV Laplacian variance
    # Rejects images too blurry for reliable OCR before wasting an API call
    try:
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            return {"error": "unreadable", "reason": "could not load image"}
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < BLUR_THRESHOLD:
            return {"error": "unreadable", "reason": "image_too_blurry", "blur_score": round(blur_score, 2)}
    except Exception as e:
        print(f"[WARN] Blur check failed: {e} - proceeding anyway")

    # STEP 2 — Rate limit gate: wait if last API call was less than 23s ago
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_INTERVAL:
        wait_time = RATE_LIMIT_INTERVAL - elapsed
        print(f"[INFO] Rate limiting: Waiting {wait_time:.1f}s...")
        time.sleep(wait_time)

    # STEP 3 — Model fallback chain: try gemini-2.5-flash first, then gemini-flash-latest
    # Falls back on quota (429) errors; breaks on other errors
    models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest']
    last_error = None

    try:
        img = Image.open(image_path)

        for model_name in models_to_try:
            try:
                print(f"[INFO] Attempting OCR with {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([RECEIPT_PROMPT, img])

                last_request_time = time.time()

                # STEP 4 — Strip markdown code fences Gemini sometimes wraps around JSON
                text_response = response.text.strip()
                if text_response.startswith("```json"):
                    text_response = text_response[7:-3].strip()
                elif text_response.startswith("```"):
                    text_response = text_response[3:-3].strip()

                result = json.loads(text_response)

                # Ensure handwriting fields are always present in successful responses
                if "error" not in result:
                    if "handwritten_flag" not in result:
                        result["handwritten_flag"] = False
                    if "handwritten_details" not in result:
                        result["handwritten_details"] = None

                    # Programmatic density anomaly check supplements Gemini's judgment.
                    # Catches localised handwritten edits Gemini may miss or under-flag.
                    density_hit, density_conf = _detect_density_anomaly(image_path)
                    if density_hit:
                        result["handwritten_flag"] = True
                        tag = f"density_anomaly(confidence={density_conf})"
                        existing = result.get("handwritten_details") or ""
                        result["handwritten_details"] = (
                            f"{existing} [{tag}]".strip() if existing else tag
                        )

                return result

            except Exception as e:
                last_error = str(e)
                if "429" in last_error or "quota" in last_error.lower():
                    print(f"[WARN] {model_name} quota exceeded. Trying fallback...")
                    continue
                else:
                    break

        last_request_time = time.time()
        return {"error": "TERMINAL_FAILURE", "message": last_error}

    except Exception as e:
        last_request_time = time.time()
        return {"error": "SYSTEM_FAILURE", "message": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_receipt_data(sys.argv[1])
        print(json.dumps(result, indent=4))
    else:
        print("Usage: python ocr.py <path_to_image>")
