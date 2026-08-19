"""
OCR Module — Team ARAJ (Ashfaaq Feroz)
Extracts structured receipt data from images using Google Gemini AI.
Pipeline: blur check → rate-limit gate → Gemini model fallback chain → JSON parse.
"""

import os
import json
import time
import base64
import tempfile
import cv2
from google import genai
from PIL import Image
from dotenv import load_dotenv

# ── ENVIRONMENT SETUP ──────────────────────────────────────────
# Load .env from ml-service/ so GEMINI_API_KEY is available
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Configure Gemini client with API key from .env
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# ── RATE LIMIT STATE ───────────────────────────────────────────
# Tracks last Gemini call time; enforces 23s gap to stay within 5 RPM free tier
last_request_time = 0
RATE_LIMIT_INTERVAL = 23  # 22s gap + 1s safety buffer

# ── BLUR DETECTION THRESHOLD ───────────────────────────────────
# Laplacian variance below this value → image too blurry to extract reliably
BLUR_THRESHOLD = 100

# Laplacian variance is not resolution-invariant: a sharp receipt shot at high
# resolution sits in a large smooth background that dilutes the whole-image
# variance below the threshold (false "unreadable"). Normalise the long edge to
# this size before scoring so the threshold means the same thing at any resolution.
BLUR_NORMALIZE_MAX_DIM = 1280

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
    # Rejects images too blurry for reliable OCR before wasting an API call.
    # If OpenCV cannot decode the format (e.g. HEIC/WEBP without codecs), we skip
    # the blur gate and let Gemini (via PIL) attempt extraction rather than reject.
    try:
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            print("[WARN] OpenCV could not decode image - skipping blur check, deferring to Gemini")
        else:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            # Normalise long edge to keep the blur score resolution-independent
            h, w = gray.shape
            longest = max(h, w)
            if longest > BLUR_NORMALIZE_MAX_DIM:
                scale = BLUR_NORMALIZE_MAX_DIM / longest
                gray = cv2.resize(gray, (int(w * scale), int(h * scale)))
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
    # Retries transient server-side failures, then falls back to the second
    # model; breaks immediately on anything that retrying cannot fix.
    #
    # 429 (quota) is not the only recoverable case. A 503 UNAVAILABLE — "this
    # model is currently experiencing high demand" — is Google's capacity, not
    # ours, and usually clears within seconds. The original loop treated it as
    # terminal and gave up without even trying the fallback model, which turned
    # a few seconds of upstream load into a failed upload.
    models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest']
    last_error = None

    # Transient: worth another attempt. Anything else (malformed request, bad
    # key, safety block) will fail identically on retry, so we stop.
    TRANSIENT = ("429", "quota", "rate limit",
                 "500", "502", "503", "504",
                 "unavailable", "overloaded", "high demand",
                 "deadline", "timeout", "internal error",
                 # An empty or non-JSON body is a malformed generation, not a
                 # malformed request — the same call usually succeeds next time.
                 "empty response", "unparseable response")
    ATTEMPTS_PER_MODEL = 3
    BACKOFF_SECONDS = (2, 6)      # after the 1st and 2nd failed attempt

    def _is_transient(msg: str) -> bool:
        low = msg.lower()
        return any(token in low for token in TRANSIENT)

    try:
        img = Image.open(image_path)

        for model_name in models_to_try:
            give_up = False

            for attempt in range(1, ATTEMPTS_PER_MODEL + 1):
                try:
                    print(f"[INFO] Attempting OCR with {model_name} "
                          f"(attempt {attempt}/{ATTEMPTS_PER_MODEL})...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[RECEIPT_PROMPT, img],
                    )

                    last_request_time = time.time()

                    # STEP 4 — Strip markdown code fences Gemini sometimes wraps around JSON
                    #
                    # response.text can be None or empty: under load, or when a
                    # safety filter or token limit truncates the candidate, the
                    # SDK still returns a response object with no usable text.
                    # Treated as transient — the same prompt usually succeeds on
                    # the next attempt — rather than crashing on .strip().
                    raw = (response.text or "").strip()
                    if not raw:
                        finish = None
                        try:
                            finish = str(response.candidates[0].finish_reason)
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"empty response from {model_name} "
                            f"(finish_reason={finish}) — treating as transient")

                    text_response = raw
                    if text_response.startswith("```json"):
                        text_response = text_response[7:-3].strip()
                    elif text_response.startswith("```"):
                        text_response = text_response[3:-3].strip()

                    # A non-JSON body is usually a truncated or prose reply, which
                    # the next attempt normally fixes. Log what actually came back
                    # so the cause is visible instead of a bare parse error.
                    try:
                        result = json.loads(text_response)
                    except json.JSONDecodeError as parse_err:
                        preview = text_response[:200].replace("\n", " ")
                        raise RuntimeError(
                            f"unparseable response from {model_name} "
                            f"({parse_err}) — treating as transient. "
                            f"Body began: {preview!r}")

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

                    # Permanent failures (bad key, malformed request, safety
                    # block) fail identically on retry — stop the whole chain.
                    if not _is_transient(last_error):
                        print(f"[ERROR] {model_name} failed permanently: {last_error}")
                        give_up = True
                        break

                    if attempt < ATTEMPTS_PER_MODEL:
                        wait = BACKOFF_SECONDS[attempt - 1]
                        print(f"[WARN] {model_name} transient failure "
                              f"({last_error[:90]}) — retrying in {wait}s")
                        time.sleep(wait)
                        continue

                    print(f"[WARN] {model_name} exhausted {ATTEMPTS_PER_MODEL} "
                          f"attempts — falling back to the next model")

            if give_up:
                break

        last_request_time = time.time()
        return {"error": "TERMINAL_FAILURE", "message": last_error}

    except Exception as e:
        last_request_time = time.time()
        return {"error": "SYSTEM_FAILURE", "message": str(e)}

# ── BASE64 ENTRY POINT (for the Node.js backend) ──────────────
# The backend holds the uploaded receipt as an in-memory base64 string and does
# not share a filesystem with this service, so it cannot pass a path. We decode
# to a short-lived temp file and run the exact same path-based pipeline above,
# then clean up — keeping the cv2/PIL layers (blur, density anomaly) unchanged.
_MIME_SUFFIX = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/heic": ".heic", "image/heif": ".heif",
}


def extract_receipt_data_from_base64(image_b64, mime_type="image/jpeg"):
    """
    Decode a base64 receipt image to a temp file and run the full OCR pipeline.
    Returns the same structured dict / error dict as extract_receipt_data().
    """
    if not api_key:
        return {"error": "GEMINI_API_KEY_MISSING"}

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return {"error": "unreadable", "reason": f"invalid base64: {e}"}

    if not image_bytes:
        return {"error": "unreadable", "reason": "empty image payload"}

    suffix = _MIME_SUFFIX.get((mime_type or "").lower().strip(), ".jpg")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        return extract_receipt_data(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                print(f"[WARN] Could not remove temp OCR file {tmp_path}: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_receipt_data(sys.argv[1])
        print(json.dumps(result, indent=4))
    else:
        print("Usage: python ocr.py <path_to_image>")
