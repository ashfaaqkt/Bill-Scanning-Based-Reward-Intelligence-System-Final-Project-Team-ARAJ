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
