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

# Keys on a paid plan, named in GEMINI_PAID_KEYS as a comma-separated list of
# variable names, e.g. "GEMINI_API_KEY_1".
#
# A billed key differs from a free one in two ways that matter here. Its
# per-minute quota is high enough that the 23-second spacing built for the free
# tier is pure latency, and it is not the shared free-tier pool, so it should be
# tried FIRST rather than taking its turn in a round robin — otherwise two out of
# every three uploads are handed to a key that is more likely to refuse.
_PAID_KEYS = {
    name.strip()
    for name in (os.getenv("GEMINI_PAID_KEYS", "") or "").split(",")
    if name.strip()
}


def _is_paid(name):
    return name in _PAID_KEYS


def _spacing_for(name):
    """Seconds this key must wait between calls."""
    return PAID_RATE_LIMIT_INTERVAL if _is_paid(name) else RATE_LIMIT_INTERVAL

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


# The SDK retries 503 ("model overloaded") internally with exponential backoff,
# so ONE generate_content call can block for over two minutes before it finally
# raises. Measured 19 Aug: a success returns in ~6s, a 503 in ~122s. That wait is
# what made the frontend look hung, and it ran out our own budget before the
# rotation could try a second key.
#
# attempts=1 turns off that inner loop, so a 503 surfaces in seconds and the
# retry decision belongs to the rotation below — which can switch key AND model,
# something the SDK's retry cannot do.
_NO_SDK_RETRY = genai_types.HttpRetryOptions(attempts=1)


def _client_for(name, value):
    state = _KEY_STATE[name]
    if state["client"] is None:
        state["client"] = genai.Client(
            api_key=value,
            http_options=genai_types.HttpOptions(retry_options=_NO_SDK_RETRY),
        )
    return state["client"]


# ── REQUEST SHAPING ────────────────────────────────────────────
# Long-edge cap for the copy sent to Gemini. 2048 keeps receipt small print
# legible while cutting a phone photo's payload by roughly 10x.
GEMINI_MAX_DIMENSION = 2048

# Which model last returned 503/stalled, and until when to deprioritise it.
# Process-local and deliberately short — capacity comes back within minutes.
_MODEL_COOLING = {}
MODEL_COOLDOWN = 120

# ── RATE LIMIT STATE ───────────────────────────────────────────
# Per-key spacing. Free keys are held to the 5 RPM ceiling; paid keys are not.
# With multiple free keys the effective wait is this divided by the number of
# usable keys.
last_request_time = 0
RATE_LIMIT_INTERVAL = 23      # free tier: 22s gap + 1s safety buffer
PAID_RATE_LIMIT_INTERVAL = 1  # billed tier: high enough limits that spacing is
                              # only a courtesy, not a constraint

# ── BLUR DETECTION ─────────────────────────────────────────────
# This gate exists to avoid spending an API call on an image the OCR cannot use.
# It is a cheap pre-filter, NOT the arbiter of readability — Gemini returns its
# own {"error": "unreadable"} and is the real judge.
#
# It used to be the plain Laplacian variance of the whole frame, thresholded at
# 100. That is an edge-energy DENSITY, not a focus measure, and it collapses for
# three reasons that have nothing to do with focus:
#   * sparse content — half a page of blank paper contributes near-zero values
#     that swamp the text (a real receipt scored 17.9 whole-frame, 26.3 over its
#     text band alone)
#   * low contrast — blue ballpoint on pink paper spans ~66 grey levels where a
#     printed thermal receipt spans ~174, and variance goes with the square
#   * handwriting — thin pen strokes carry far less energy than printed glyphs
# It rejected 12 of Jyoti's 100 real receipts before Gemini ever saw them.
#
# The measure below normalises contrast first, then scores only the strongest 5%
# of edge pixels — where the ink actually is. Blank paper no longer votes.
BLUR_NORMALIZE_MAX_DIM = 1280   # long edge, so the score is resolution-independent
BLUR_EDGE_PERCENTILE = 95       # keep the top 5% of edge pixels = the ink
BLUR_CONTRAST_PCT = (2, 98)     # percentile stretch, robust to specks and glare

# Calibrated against Gemini itself: 100 real receipts plus Gaussian-blurred
# copies at sigma 1.8-6.0, scored and then actually sent for extraction
# (ml-service/calibrate_blur_gate.py regenerates every number).
#
# The two classes overlap heavily — Receipt 10 at sigma 2.5 (score 80.7) came
# back unreadable while the BLURRIER sigma 3.0 copy (score 49.5) extracted fine.
# Gemini's verdict is not deterministic near the boundary, so no threshold can
# separate readable from unreadable, and any attempt to place one in the overlap
# band refuses receipts that would have worked.
#
# So the threshold sits below the lowest score that ever produced a successful
# extraction (49.5), catching only the unambiguously hopeless. The asymmetry
# justifies it: a false reject blocks a user from claiming a valid bill, while a
# false admit costs one API call and roughly two seconds before Gemini says the
# same thing. All 100 real receipts now pass.
BLUR_THRESHOLD = 40

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

# ── BLUR SCORE ─────────────────────────────────────────────────
def _blur_score(gray):
    """How sharp the ink is, independent of how much ink there is.

    Returns mean squared Laplacian over the ink pixels of a contrast-normalised
    image. Higher is sharper. See the BLUR_* constants for why it is measured
    this way and how the threshold was calibrated.
    """
    h, w = gray.shape
    longest = max(h, w)
    if longest > BLUR_NORMALIZE_MAX_DIM:
        scale = BLUR_NORMALIZE_MAX_DIM / longest
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)))

    # Stretch contrast so pale ink on tinted paper is judged on sharpness rather
    # than on how dark it happens to be. Percentiles rather than min/max, so one
    # glare speck or dust mote cannot set the scale.
    g = gray.astype(np.float64)
    lo, hi = np.percentile(g, BLUR_CONTRAST_PCT[0]), np.percentile(g, BLUR_CONTRAST_PCT[1])
    if hi - lo < 1:
        return 0.0                      # blank or uniform frame: nothing to read
    g = np.clip((g - lo) * 255.0 / (hi - lo), 0, 255)

    # Score only where there is ink. Averaging over the whole frame lets blank
    # paper outvote the text, which is what broke the old measure.
    lap = np.abs(cv2.Laplacian(g, cv2.CV_64F))
    ink = lap[lap >= np.percentile(lap, BLUR_EDGE_PERCENTILE)]
    return float((ink ** 2).mean()) if ink.size else 0.0


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
            blur_score = _blur_score(gray)
            if blur_score < BLUR_THRESHOLD:
                print(f"[INFO] Rejected before OCR: blur score {blur_score:.1f} "
                      f"< {BLUR_THRESHOLD}")
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
    # Ordered best-quality-first, but the order is only a starting point: which
    # model is saturated changes through the day. Measured 19 Aug 17:40 —
    # flash-latest returned 503 while 2.5-flash answered in 1.2s; earlier the
    # same week it was the other way round. _MODEL_COOLING below reorders on
    # what is actually failing right now, so a saturated model is skipped rather
    # than retried first on every upload.
    models_to_try = ['gemini-2.5-flash',
                     'gemini-flash-latest',
                     'gemini-flash-lite-latest']

    # "timed out" is spelled separately from "timeout" on purpose: the socket
    # raises "The read operation timed out", which matched none of these and so
    # classified as permanent — the rotation broke after a single attempt with
    # 70s of budget unspent. Any of these means try again, not give up.
    TRANSIENT = ("500", "502", "503", "504",
                 "unavailable", "overloaded", "high demand",
                 "deadline", "timeout", "timed out", "internal error",
                 "connection", "temporarily",
                 "empty response", "unparseable response")
    QUOTA = ("429", "resource_exhausted", "exceeded your current quota",
             "rate limit")
    UNSUPPORTED = ("404", "not_found", "no longer available")

    # Measured 19 Aug against the billed key: a success returns in 4-6s, while a
    # struggling request can sit for 60s+ before yielding 503. So cap each call
    # well above the success time but far below the stall time, and spend the
    # budget on ROTATING instead of waiting — a different key/model pair is far
    # likelier to succeed than the same one given longer.
    DEADLINE_SECONDS = 90
    # Per-call ceiling. Without it the deadline is only checked BETWEEN
    # attempts, so one slow call cannot be interrupted — a request was observed
    # running 93 seconds past its budget because a single call hung that long.
    #
    # Sized from measurement, not taste. A 503 rejection alone takes about 12
    # seconds, and a full receipt extraction returns a long JSON body, so an
    # earlier 15-second ceiling was cutting off calls that would have succeeded
    # and reporting them as "read operation timed out". 30 seconds clears a real
    # extraction; the 70-second budget then affords roughly two attempts.
    CALL_TIMEOUT_SECONDS = 20
    # A failure now costs seconds rather than two minutes, so the budget buys a
    # real walk across the combinations instead of one slow attempt.
    MAX_ATTEMPTS = 6              # 3 keys x 2 models
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
        # Paid first, then least recently used within each group.
        return min(usable, key=lambda kv: (not _is_paid(kv[0]),
                                           _KEY_STATE[kv[0]]["last_used"]))

    if not _API_KEYS:
        return {"error": "GEMINI_API_KEY_MISSING"}

    deadline = time.time() + DEADLINE_SECONDS
    last_error = None
    saw_quota = False
    attempted = set()          # (key, model) pairs tried during this request

    try:
        img = Image.open(image_path)

        # Phone cameras produce 4284x5712 files (~2.8 MB encoded). Gemini tiles
        # vision input at a far lower resolution, so the extra pixels buy no
        # accuracy and cost upload seconds on every retry. Capping the long edge
        # took one test receipt from 2847 KB to 274 KB.
        #
        # The full-resolution image is untouched for the blur and density checks
        # — only the network payload shrinks.
        if max(img.size) > GEMINI_MAX_DIMENSION:
            img = img.copy()
            img.thumbnail((GEMINI_MAX_DIMENSION, GEMINI_MAX_DIMENSION),
                          Image.LANCZOS)

        attempt = 0

        while attempt < MAX_ATTEMPTS and time.time() < deadline:
            now = time.time()

            # Rotate over (model, key) COMBINATIONS, not keys alone. Cycling
            # three keys against one model only ever tests one model, and the
            # two differ in availability — 2.5-flash has served this pipeline
            # when flash-latest was saturated. Prefer a pair not yet tried.
            # Skip models seen 503-ing in the last MODEL_COOLDOWN seconds.
            # Falls back to the full list if that would leave nothing.
            ranked = [m for m in models_to_try
                      if _MODEL_COOLING.get(m, 0) <= now] or models_to_try

            combo = None
            for m in ranked:
                name, value = _pick_key(now, m)
                if name and (name, m) not in attempted:
                    combo = (m, name, value)
                    break
            if combo is None:                      # everything tried once
                for m in ranked:
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
            gap = _spacing_for(key_name) - (now - state["last_used"])
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
                            timeout=int(call_timeout * 1000),  # milliseconds
                            retry_options=_NO_SDK_RETRY,
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

                # Transient here means the model was overloaded or stalled;
                # remember that so the NEXT upload does not lead with it.
                _MODEL_COOLING[model_name] = time.time() + MODEL_COOLDOWN

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
