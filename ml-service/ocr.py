import os
import json
import time
import cv2
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Explicitly load .env from the ml-service directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Global state for rate limiting
last_request_time = 0
RATE_LIMIT_INTERVAL = 23  # Increased slightly (22s + 1s buffer) for safety

BLUR_THRESHOLD = 100  # Laplacian variance below this → image is too blurry to process

# Define the extraction prompt once
RECEIPT_PROMPT = (
    "Analyze this receipt image and extract the following details into a strict JSON format. "
    "If the image is blurry or unreadable, return exactly: {\"error\": \"unreadable\"}. "
    "Otherwise return: "
    "{"
    "\"rawMerchant\": \"string\", "
    "\"date\": \"string (YYYY-MM-DD)\", "
    "\"total\": number, "
    "\"category\": \"string ('Supermarket / Grocery', 'Food & Beverage', or 'General Retail')\", "
    "\"items\": [{ \"name\": \"string\", \"price\": number }]"
    "}"
)

def extract_receipt_data(image_path):
    """
    Extracts structured JSON data from a receipt image using Gemini AI.
    Tries gemini-2.5-flash first, falls back to gemini-flash-latest (1.5) on quota exhaustion.
    """
    global last_request_time

    if not api_key:
        return {"error": "GEMINI_API_KEY_MISSING"}

    # Blur detection via Laplacian variance (OpenCV)
    try:
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            return {"error": "unreadable", "reason": "could not load image"}
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        print(f"[INFO] Blur score (Laplacian variance): {blur_score:.2f}")
        if blur_score < BLUR_THRESHOLD:
            print(f"[WARN] Image rejected — blur score {blur_score:.2f} below threshold {BLUR_THRESHOLD}")
            return {"error": "unreadable", "reason": "image_too_blurry", "blur_score": round(blur_score, 2)}
    except Exception as e:
        print(f"[WARN] Blur check failed: {e} — proceeding anyway")

    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_INTERVAL:
        wait_time = RATE_LIMIT_INTERVAL - elapsed
        print(f"[INFO] Rate limiting: Waiting {wait_time:.1f}s...")
        time.sleep(wait_time)

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
                
                text_response = response.text.strip()
                # Clean markdown formatting if present
                if text_response.startswith("```json"):
                    text_response = text_response[7:-3].strip()
                elif text_response.startswith("```"):
                    text_response = text_response[3:-3].strip()
                    
                return json.loads(text_response)

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
