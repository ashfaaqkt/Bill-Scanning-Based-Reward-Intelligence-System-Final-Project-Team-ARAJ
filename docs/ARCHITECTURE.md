# System Architecture — Team ARAJ

## High-Level Overview

```
User (Browser)
      │
      ▼
┌─────────────────────────┐
│   Frontend              │  Static HTML/CSS/JS
│   frontend/             │  Firebase Auth (client-side)
└───────────┬─────────────┘
            │ HTTP
            ▼
┌─────────────────────────┐
│   Backend               │  Node.js + Express
│   backend/server.js     │  Firebase Admin SDK
│                         │  JWT Auth middleware
│                         │  Delegates OCR → ml-service /ml/ocr
└───────────┬─────────────┘
            │ HTTP (internal)
            ▼
┌─────────────────────────┐
│   ML Service            │  Python Flask
│   ml-service/app.py     │  ocr.py → Gemini 2.5 Flash (OCR + extraction)
│                         │  scikit-learn models
│                         │  Routes: /ml/*
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│   Firebase / Firestore  │  User data, receipts, rewards
└─────────────────────────┘
```

## Data Flow: Receipt Upload (current implementation)

1. Frontend sends the receipt as base64 to `POST /api/upload`
2. Backend validates the image (MIME + base64 + byte sniff) in memory — no `uploads/` folder
3. Backend calls `POST /ml/ocr` — **ocr.py** runs the 5-layer pipeline (blur → rate-limit → Gemini 2.5 Flash → multi-bill / handwriting / density anomaly) and returns structured JSON
4. Backend calls `POST /ml/classify` — **classifier.py** (trained Notebook 02) sets the category when confident (confidence ≥ 0.65); otherwise the Gemini category is kept
5. Backend does dedup and computes reward points. Three checks run in order: a per-user SHA-256 fingerprint, a fuzzy merchant match (Levenshtein + Jaccard, 0.84), and a **cross-user** fingerprint check. The third **rejects the upload with 409 `ALREADY_CLAIMED`** — one physical receipt earns a reward once, so a bill already claimed on another account is not scored, not stored and not paid; the attempt is written to `Fraud_Scores` with `blocked: true`
6. Backend writes receipt + line items + logs to Firestore
7. Backend calls `POST /ml/fraud-score` — passes the OCR result (incl. `handwritten_flag`), **the image**, and the perceptual hashes of the last 300 receipts. All three matter: without the image the tamper CNN and the pHash check score nothing, and without the hashes the duplicate check has nothing to compare against. The service returns the fraud probability (banded `Low` / `Medium` / `High`), the CNN's own `tamper_probability`, and this image's `image_phash`, which the backend stores on the receipt so the next upload can be compared against it
8. Backend calls `POST /ml/anomaly` — Isolation Forest over the amount → `anomalyScore` + `anomalyFlag`. An items/total mismatch or an anomaly flag raises `Low` to `Medium`
9. Backend calls `POST /ml/update-profile` — **awaited, not fire-and-forget**, so the recommendations in step 10 reflect the receipt just scanned
10. Backend calls `POST /ml/recommend` → offers ranked against that interest vector
11. Response sent back to frontend with the extracted data, the reward result (`category` + `gemini_category`), the verification verdict (`fraudScore`, `riskLevel`, `anomalyScore`, `anomalyFlag`, `crossUserDuplicate`, `itemsTotalMismatch`) and `recommendedRewards`

> The web client renders the verification verdict in the results panel — risk badge, the composite fraud score, anomaly state and a one-line reason naming every signal that fired. Full response schema: [`API.md`](API.md).

> **Wired:** `/ml/classify` is now called from `/api/upload` — the trained Notebook 02 classifier sets the category when it is confident (confidence ≥ 0.65), otherwise the OCR/Gemini category is kept (both are returned as `category` + `gemini_category`).
> **All five ML endpoints are wired and backed by trained logic.** `/ml/anomaly` runs a trained Isolation Forest; `/ml/recommend` returns offers ranked against the user's interest vector, and is called both from `/api/upload` (as `data.recommendedRewards`) and from `GET /api/recommendations`. The **SVD collaborative filter landed with NB 04 (Aug 19)** and is blended 50/50 with content affinity, so `/ml/recommend` reports `model: "collaborative+content"`. Its offline score is not claimed against the NDCG target — the interactions it trains and evaluates on are synthetic.
>
> **Two seams were found broken and fixed, both invisible to component tests.** `/ml/fraud-score` was called without the image, so the tamper CNN never ran on an upload (fixed Aug 19); and no perceptual hash was ever stored or sent, so the duplicate check returned false on every upload from the day it was written (fixed Aug 19). Each module passed its own tests throughout.

## ML Pipeline (ml-service)

```
Receipt Image
      │
      ├── ocr.py          → Gemini 2.5 Flash + blur / multi-bill / handwriting  [LIVE, wired]
      │
      ├── fraud.py        → OCR signals + pHash + tamper CNN @448    [LIVE, AUC 0.805]
      │                     returns image_phash so the backend can store it
      │
      ├── forensics.py    → 31 hand-designed forensic features       [built, not served]
      │
      ├── classifier.py   → TF-IDF + Random Forest → category label   [LIVE, macro-F1 0.942]
      │
      ├── anomaly.py      → Isolation Forest → spending anomaly score [LIVE, FPR 13.2%]
      │
      ├── user_profile.py → per-user interest vector (decayed)        [LIVE]
      │
      └── recommend.py    → content + SVD collaborative blend → top-N [LIVE, hybrid]
```

### Model status

| Component | Algorithm | Result | Target |
|---|---|---|---|
| Category classifier | TF-IDF + Random Forest | macro-F1 **0.942** / acc 0.944 | 0.80 ✅ |
| Anomaly detector | Isolation Forest (beat OC-SVM, LOF) | FPR **13.2%**, 100% recall ≥10× | <15% ✅ |
| Fraud tamper CNN | MobileNetV2 @ 448×448 | AUC **0.805** (0.864 real receipts) | 0.90 ⚠️ |
| Recommender | Hybrid — content affinity + SVD (NB 04) | 5-fold CV RMSE **0.9157** | RMSE < 0.5 / < 1.0 🔸 not claimed |
| Reward ranker | Evaluation harness (NB 05), not a trained ranker | NDCG@5 **0.7984** on synthetic data | NDCG@5 > 0.70 🔸 cleared, not claimed |

Full detail per model: [`report/model_cards/`](../report/model_cards/README.md).

**Training the fraud CNN at 448×448 rather than the usual 224 is the single
largest modelling decision.** Receipts are ~1200×1600, so 224 is a 7.1× downscale
that reduces an overwritten digit to ~6 pixels. `fraud.py` therefore resizes to
448 at serving time via one shared `IMG_SIZE` constant — serving at 224 a model
trained at 448 would silently degrade every prediction.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JS, Firebase Auth |
| Backend | Node.js 20, Express 5, Firebase Admin (OCR delegated to ml-service) |
| ML Service | Python 3.13, Flask, Gemini (2.5-flash / flash-latest / flash-lite-latest), OpenCV, scikit-learn, PyTorch |
| Database | Firebase Firestore |
| Auth | Firebase Auth + JWT |
| Dataset | CORD, SROIE, Indian receipts |
| Notebooks | Jupyter, pandas, matplotlib |
