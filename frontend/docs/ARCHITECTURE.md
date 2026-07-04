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
4. Backend does dedup (SHA-256 fingerprint + fuzzy merchant) and computes reward points
5. Backend writes receipt + line items + logs to Firestore
6. Backend calls `POST /ml/fraud-score` — passes the OCR result (incl. `handwritten_flag`) → fraud probability
7. Backend calls `POST /ml/update-profile` (fire-and-forget) to update the user interest vector
8. Response sent back to frontend with extracted data + reward result

> **Not yet wired:** `/ml/classify`, `/ml/anomaly`, `/ml/recommend` exist as routes but are not called from `/api/upload` yet — category currently comes from the OCR step, and reward offers are static. These get wired once the models are trained.

## ML Pipeline (ml-service)

```
Receipt Image
      │
      ├── ocr.py          → Gemini 2.5 Flash + blur / multi-bill / handwriting  [LIVE, wired]
      │
      ├── fraud.py        → OCR-signal fraud score [LIVE]; pHash + tamper CNN [stub]
      │
      ├── classifier.py   → TF-IDF + Random Forest → category label   [stub, not wired]
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
