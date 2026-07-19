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
7. Backend calls `POST /ml/fraud-score` — passes the OCR result (incl. `handwritten_flag`) → fraud probability
8. Backend calls `POST /ml/update-profile` (fire-and-forget) to update the user interest vector
9. Response sent back to frontend with extracted data + reward result (category + gemini_category)

> **Wired:** `/ml/classify` is now called from `/api/upload` — the trained Notebook 02 classifier sets the category when it is confident (confidence ≥ 0.45), otherwise the OCR/Gemini category is kept (both are returned as `category` + `gemini_category`).
> **Not yet wired:** `/ml/anomaly` and `/ml/recommend` exist as routes but are not called yet — anomaly scoring is unused and reward offers are still static. These get wired once their models (NB 03/04/05) are trained.

## ML Pipeline (ml-service)

```
Receipt Image
      │
      ├── ocr.py          → Gemini 2.5 Flash + blur / multi-bill / handwriting  [LIVE, wired]
      │
      ├── fraud.py        → OCR-signal fraud score [LIVE]; pHash + tamper CNN [stub]
      │
      ├── classifier.py   → TF-IDF + Random Forest → category label   [TRAINED + WIRED, conf-gated]
      │
      ├── anomaly.py      → Isolation Forest → spending anomaly score  [stub, not wired]
      │
      ├── user_profile.py → interest vector update                    [stub, wired]
      │
      └── recommend.py    → SVD + reward ranker → top-N offers         [stub, not wired]
```

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
