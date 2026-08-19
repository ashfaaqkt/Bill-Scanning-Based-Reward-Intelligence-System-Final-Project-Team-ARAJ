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
import numpy as np
from google import genai
from google.genai import types as genai_types
from PIL import Image
from dotenv import load_dotenv

# HEIC/HEIF is the iPhone camera default, and the backend accepts it — but
# neither OpenCV nor stock Pillow can decode it, so every iPhone upload failed
# with "cannot identify image file". Registering the opener teaches Pillow the
# format; if the package is unavailable the pipeline still runs for JPEG/PNG
# rather than refusing to start.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    _HEIF_SUPPORTED = True
except ImportError:                                   # pragma: no cover
    _HEIF_SUPPORTED = False
    print("[WARN] pillow-heif not installed — HEIC/HEIF uploads will be rejected")

# ── ENVIRONMENT SETUP ──────────────────────────────────────────
# Load .env from ml-service/ so GEMINI_API_KEY is available
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# ── API KEY POOL ───────────────────────────────────────────────
# Reads GEMINI_API_KEY_1, _2, _3 … and falls back to a single GEMINI_API_KEY,
# so an installation with one key behaves exactly as before.
#
# The free tier allows five requests per minute PER PROJECT. Keys issued from
# separate projects therefore have separate quotas, and rotating across them
# multiplies the ceiling: the spacing each key needs is unchanged, but with N
# keys a request only waits RATE_LIMIT_INTERVAL / N on average.
#
# Rotation also turns a 429 from fatal into routine — an exhausted key is put
# on ice and the next one serves the request, instead of the upload failing.
def _load_api_keys():
    keys, seen = [], set()
    for name in sorted(k for k in os.environ if k.startswith("GEMINI_API_KEY")):
        value = (os.environ.get(name) or "").strip()
        if value and value not in seen:
            seen.add(value)
            keys.append((name, value))
    return keys


_API_KEYS = _load_api_keys()

# Per-key state. `cooling_until` is set when a key reports quota exhaustion, so
# it is skipped until its window has plausibly reset rather than retried into
# the ground. `unsupported` records model names a key cannot serve — newer
# projects are refused gemini-2.5-flash with a 404, and there is no point
# rediscovering that on every upload.
_KEY_STATE = {
    name: {"client": None, "last_used": 0.0, "cooling_until": 0.0,
           "unsupported": set()}
    for name, _ in _API_KEYS
}

# Kept for callers and tests that check whether OCR is configured at all.
api_key = _API_KEYS[0][1] if _API_KEYS else None
client = None


def _client_for(name, value):
    state = _KEY_STATE[name]
    if state["client"] is None:
        state["client"] = genai.Client(api_key=value)
    return state["client"]


# ── RATE LIMIT STATE ───────────────────────────────────────────
# Per-key spacing to stay within the 5 RPM free tier. With multiple keys the
# effective wait is this divided by the number of usable keys.
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
            # OpenCV has no HEIC codec, but Pillow now does. Decoding through
            # Pillow keeps the blur gate working for iPhone photos instead of
            # waving them through and spending an API call on an unreadable one.
            try:
                with Image.open(image_path) as pil_img:
                    img_cv = cv2.cvtColor(np.array(pil_img.convert("RGB")),
                                          cv2.COLOR_RGB2BGR)
                print("[INFO] Decoded via Pillow for the blur check "
                      "(OpenCV lacks this codec)")
            except Exception as pil_err:
                print(f"[WARN] Neither OpenCV nor Pillow could decode the image "
                      f"({pil_err}) — skipping blur check, deferring to Gemini")

        if img_cv is None:
            pass                      # blur gate skipped; Gemini will decide
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

    # STEP 2/3 — Pick a key, respect its spacing, call, rotate on failure.
    #
    # Ordering matters here and was established by testing the keys directly:
    #
    #   * gemini-flash-latest goes FIRST. gemini-2.5-flash is refused with a 404
    #     — "no longer available to new users" — by projects created recently,
    #     so it cannot be the default when keys come from different projects.
    #   * A 404 marks that model unusable FOR THAT KEY only, and the next model
    #     is tried. It is a capability difference, not a fault.
    #   * A 429 puts the key on ice and moves to the next key. With one key that
    #     ends the request; with three it is usually invisible.
    #   * A 503 is Google's capacity and is shared across projects, so another
    #     key rarely helps — but it costs nothing to let the rotation try.
    models_to_try = ['gemini-flash-latest', 'gemini-2.5-flash']

    TRANSIENT = ("500", "502", "503", "504",
                 "unavailable", "overloaded", "high demand",
                 "deadline", "timeout", "internal error",
                 "empty response", "unparseable response")
    QUOTA = ("429", "resource_exhausted", "exceeded your current quota",
             "rate limit")
    UNSUPPORTED = ("404", "not_found", "no longer available")

    DEADLINE_SECONDS = 70
    # Per-call ceiling. Without it the deadline is only checked BETWEEN
    # attempts, so one slow call cannot be interrupted — a request was observed
    # running 93 seconds past its budget because a single call hung that long.
    #
    # Sized from measurement, not taste. A 503 rejection alone takes about 12
    # seconds, and a full receipt extraction returns a long JSON body, so an
    # earlier 15-second ceiling was cutting off calls that would have succeeded
    # and reporting them as "read operation timed out". 30 seconds clears a real
    # extraction; the 70-second budget then affords roughly two attempts.
    CALL_TIMEOUT_SECONDS = 30
    MAX_ATTEMPTS = 4              # across all key/model combinations
    BACKOFF_SECONDS = 2
    QUOTA_COOLDOWN = 65           # a per-minute window, plus a margin

    def _classify(msg):
        low = msg.lower()
        if any(t in low for t in UNSUPPORTED):
            return "unsupported"
        if any(t in low for t in QUOTA):
            return "quota"
        if any(t in low for t in TRANSIENT):
            return "transient"
        return "permanent"

    def _pick_key(now, model):
        """Least recently used key that is not cooling and can serve `model`."""
        usable = [
            (name, value) for name, value in _API_KEYS
            if _KEY_STATE[name]["cooling_until"] <= now
            and model not in _KEY_STATE[name]["unsupported"]
        ]
        if not usable:
            return None, None
        return min(usable, key=lambda kv: _KEY_STATE[kv[0]]["last_used"])

    if not _API_KEYS:
        return {"error": "GEMINI_API_KEY_MISSING"}

    deadline = time.time() + DEADLINE_SECONDS
    last_error = None
    saw_quota = False
    attempted = set()          # (key, model) pairs tried during this request

    try:
        img = Image.open(image_path)
        attempt = 0

        while attempt < MAX_ATTEMPTS and time.time() < deadline:
            now = time.time()

            # Rotate over (model, key) COMBINATIONS, not keys alone. Cycling
            # three keys against one model only ever tests one model, and the
            # two differ in availability — 2.5-flash has served this pipeline
            # when flash-latest was saturated. Prefer a pair not yet tried.
            combo = None
            for m in models_to_try:
                name, value = _pick_key(now, m)
                if name and (name, m) not in attempted:
                    combo = (m, name, value)
                    break
            if combo is None:                      # everything tried once
                for m in models_to_try:
                    name, value = _pick_key(now, m)
                    if name:
                        combo = (m, name, value)
                        break
            if combo is None:
                last_error = last_error or "every key is cooling or unsupported"
                break

            model_name, key_name, key_value = combo
            attempted.add((key_name, model_name))
            state = _KEY_STATE[key_name]
            attempt += 1

            # Each key needs its own spacing; rotation is what makes the wait
            # short, not a shorter interval.
            gap = RATE_LIMIT_INTERVAL - (now - state["last_used"])
            if gap > 0:
                if now + gap > deadline:
                    last_error = (last_error or
                                  f"{key_name} needs {gap:.0f}s spacing, "
                                  f"beyond the time budget")
                    print(f"[WARN] Stopping: {key_name} needs {gap:.0f}s but "
                          f"{deadline - now:.0f}s of budget remains")
                    break
                print(f"[INFO] Spacing {key_name}: waiting {gap:.1f}s...")
                time.sleep(gap)

            try:
                print(f"[INFO] OCR attempt {attempt}/{MAX_ATTEMPTS} — "
                      f"{model_name} via {key_name}")
                state["last_used"] = time.time()
                last_request_time = state["last_used"]

                # Cap the call at whichever is smaller: the per-call ceiling or
                # what remains of the overall budget.
                budget_left = max(1.0, deadline - time.time())
                call_timeout = min(CALL_TIMEOUT_SECONDS, budget_left)

                response = _client_for(key_name, key_value).models.generate_content(
                    model=model_name,
                    contents=[RECEIPT_PROMPT, img],
                    config=genai_types.GenerateContentConfig(
                        http_options=genai_types.HttpOptions(
                            timeout=int(call_timeout * 1000)   # milliseconds
                        )
                    ),
                )

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

                # STEP 4 — Strip markdown code fences Gemini sometimes wraps around JSON
                text_response = raw
                if text_response.startswith("```json"):
                    text_response = text_response[7:-3].strip()
                elif text_response.startswith("```"):
                    text_response = text_response[3:-3].strip()

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

                print(f"[INFO] OCR succeeded on {key_name} ({model_name})")
                return result

            except Exception as e:
                last_error = str(e)
                kind = _classify(last_error)

                if kind == "unsupported":
                    state["unsupported"].add(model_name)
                    print(f"[INFO] {key_name} cannot serve {model_name} — "
                          f"remembering, trying another combination")
                    continue

                if kind == "quota":
                    saw_quota = True
                    state["cooling_until"] = time.time() + QUOTA_COOLDOWN
                    print(f"[WARN] {key_name} quota exhausted — cooling for "
                          f"{QUOTA_COOLDOWN}s, rotating to the next key")
                    continue

                if kind == "permanent":
                    print(f"[ERROR] {key_name}/{model_name} failed permanently: "
                          f"{last_error[:120]}")
                    break

                remaining = deadline - time.time()
                if attempt >= MAX_ATTEMPTS or remaining <= BACKOFF_SECONDS:
                    print(f"[WARN] transient failure, budget spent "
                          f"({remaining:.0f}s left) — giving up")
                    break
                print(f"[WARN] {key_name}/{model_name} transient "
                      f"({last_error[:80]}) — {remaining:.0f}s left, "
                      f"retrying in {BACKOFF_SECONDS}s")
                time.sleep(BACKOFF_SECONDS)

        # Report the condition that is ACTUALLY blocking, not merely one that was
        # seen along the way. Reporting RATE_LIMITED because a single key hit its
        # quota — while the others failed on 503 — tells the user to wait a
        # minute for a problem that waiting does not fix, and hides the real
        # cause. Quota is only the blocker when it has taken every key out.
        now = time.time()
        usable = [n for n, _ in _API_KEYS if _KEY_STATE[n]["cooling_until"] <= now]
        if saw_quota and not usable:
            print("[ERROR] Every key is quota-exhausted — reporting rate limit")
            return {"error": "RATE_LIMITED", "message": last_error}

        if saw_quota:
            print(f"[INFO] A key hit quota, but {len(usable)} key(s) remain "
                  f"usable — the blocking failure was: {(last_error or '')[:90]}")
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
