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
4. Backend calls `POST /ml/classify` — **classifier.py** (trained Notebook 02) sets the category when confident (confidence ≥ 0.45); otherwise the Gemini category is kept
5. Backend does dedup (SHA-256 fingerprint + fuzzy merchant) and computes reward points
6. Backend writes receipt + line items + logs to Firestore
7. Backend calls `POST /ml/fraud-score` — passes the OCR result (incl. `handwritten_flag`) → fraud probability, banded into `Low` / `Medium` / `High`
8. Backend calls `POST /ml/anomaly` — Isolation Forest over the amount → `anomalyScore` + `anomalyFlag`. A cross-user duplicate forces risk to `High`; an items/total mismatch or an anomaly flag raises `Low` to `Medium`
9. Backend calls `POST /ml/update-profile` — **awaited, not fire-and-forget**, so the recommendations in step 10 reflect the receipt just scanned
10. Backend calls `POST /ml/recommend` → offers ranked against that interest vector
11. Response sent back to frontend with the extracted data, the reward result (`category` + `gemini_category`), the verification verdict (`fraudScore`, `riskLevel`, `anomalyScore`, `anomalyFlag`, `crossUserDuplicate`, `itemsTotalMismatch`) and `recommendedRewards`

> The web client renders the verification verdict in the results panel — risk badge, tamper score, anomaly state and a one-line reason. Full response schema: [`API.md`](API.md).

> **Wired:** `/ml/classify` is now called from `/api/upload` — the trained Notebook 02 classifier sets the category when it is confident (confidence ≥ 0.45), otherwise the OCR/Gemini category is kept (both are returned as `category` + `gemini_category`).
> **All five ML endpoints are now wired and backed by trained logic (Aug 7, 2026).** `/ml/anomaly` runs a trained Isolation Forest; `/ml/recommend` returns offers ranked against the user's interest vector, and is called both from `/api/upload` (as `data.recommendedRewards`) and from the new `GET /api/recommendations`. The one component still awaiting a model is the **SVD collaborative filter** (NB 04) — `recommend.py` ranks content-based until it ships.

## ML Pipeline (ml-service)

```
Receipt Image
      │
      ├── ocr.py          → Gemini 2.5 Flash + blur / multi-bill / handwriting  [LIVE, wired]
      │
      ├── fraud.py        → OCR signals + pHash + tamper CNN @448    [LIVE, AUC 0.805]
      │
      ├── forensics.py    → 31 hand-designed forensic features       [built, not served]
      │
      ├── classifier.py   → TF-IDF + Random Forest → category label   [LIVE, macro-F1 0.942]
      │
      ├── anomaly.py      → Isolation Forest → spending anomaly score [LIVE, FPR 13.2%]
      │
      ├── user_profile.py → per-user interest vector (decayed)        [LIVE]
      │
      └── recommend.py    → content-based offer ranking → top-N       [LIVE; SVD pending NB 04]
```

### Model status

| Component | Algorithm | Result | Target |
|---|---|---|---|
| Category classifier | TF-IDF + Random Forest | macro-F1 **0.942** / acc 0.944 | 0.80 ✅ |
| Anomaly detector | Isolation Forest (beat OC-SVM, LOF) | FPR **13.2%**, 100% recall ≥10× | <15% ✅ |
| Fraud tamper CNN | MobileNetV2 @ 448×448 | AUC **0.805** (0.864 real receipts) | 0.90 ⚠️ |
| Recommender | content-based ranking (not trained) | no offline metric possible | NDCG ⏳ |
| Reward ranker | — | not started (NB 05) | — |

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
| ML Service | Python 3.10+, Flask, Gemini 2.5 Flash, OpenCV, scikit-learn |
| Database | Firebase Firestore |
| Auth | Firebase Auth + JWT |
| Dataset | CORD, SROIE, Indian receipts |
| Notebooks | Jupyter, pandas, matplotlib |
