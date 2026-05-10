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
│                         │  Gemini API (OCR + extraction)
│                         │  JWT Auth middleware
└───────────┬─────────────┘
            │ HTTP (internal)
            ▼
┌─────────────────────────┐
│   ML Service            │  Python Flask
│   ml-service/app.py     │  scikit-learn
│                         │  Routes: /ml/*
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│   Firebase / Firestore  │  User data, receipts, rewards
└─────────────────────────┘
```

## Data Flow: Receipt Upload

1. User uploads receipt image via frontend
2. Backend receives image, saves to `uploads/`
3. Backend calls Gemini API for OCR + structured extraction
4. Backend calls `/ml/fraud-score` — ML service returns fraud probability
5. If fraud score < threshold, backend calls `/ml/classify` for category
6. Backend calls `/ml/update-profile` to update user interest vector
7. Backend stores receipt + metadata in Firestore
8. Backend calls `/ml/recommend` — returns ranked reward offers
9. Response sent back to frontend with extracted data + recommendations

## ML Pipeline (ml-service)

```
Receipt Image
      │
      ├── fraud.py        → blur check, phash duplicate, tamper CNN
      │
      ├── classifier.py   → TF-IDF + Random Forest → category label
      │
      ├── anomaly.py      → Isolation Forest → spending anomaly score
      │
      ├── user_profile.py → interest vector update (online learning)
      │
      └── recommend.py    → reward ranker → top-N offers
```

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JS, Firebase Auth |
| Backend | Node.js 20, Express 4, Firebase Admin, Gemini API |
| ML Service | Python 3.10, Flask, scikit-learn |
| Database | Firebase Firestore |
| Auth | Firebase Auth + JWT |
| Dataset | CORD, SROIE, Indian receipts |
| Notebooks | Jupyter, pandas, matplotlib |
