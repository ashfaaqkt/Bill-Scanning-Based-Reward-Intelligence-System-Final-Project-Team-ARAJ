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
3. Backend calls `POST /ml/ocr` — **ocr.py** runs the 5-layer pipeline (sharpness gate → rate-limit → Gemini 2.5 Flash → multi-bill / handwriting / density anomaly). The sharpness gate refuses an unreadable photo **before any API call is spent**, returning `IMAGE_TOO_BLURRY`
4. Backend calls `POST /ml/classify` — **classifier.py** (trained Notebook 02) sets the category when confident (confidence ≥ 0.65); otherwise the Gemini category is kept
5. **Four Firestore reads issue together** — per-user fingerprint, fuzzy merchant candidates, cross-user fingerprint, and the perceptual hashes of the last 300 receipts. None depends on another, so they cost one round trip rather than four
6. Dedup applies in order: per-user fingerprint → fuzzy merchant match (Levenshtein + Jaccard, 0.84) → **cross-user** fingerprint. The third refuses the upload with 409 `ALREADY_CLAIMED`
7. **Fraud and anomaly scoring run together, and BEFORE anything is written.** `/ml/fraud-score` receives the OCR result (incl. `handwritten_flag`), **the image**, and the hash+total pairs from step 5; `/ml/anomaly` runs an Isolation Forest over the amount. Both inputs matter: without the image the tamper CNN and the pHash check score nothing, and without the pairs the duplicate check has nothing to compare against
8. If the perceptual hash matches a stored receipt **and the totals agree**, the upload is refused with 409 `DUPLICATE_IMAGE`. Scoring precedes the writes precisely so that a refusal leaves nothing behind
9. **All six writes commit in one atomic batch** — merchant, receipt, line items, points, consent log, fraud score. These were six sequential round trips; batching is both faster and all-or-nothing, so a mid-sequence failure can no longer leave a receipt with no points
10. Backend calls `POST /ml/update-profile` — **awaited, not fire-and-forget**, so the recommendations below reflect the receipt just scanned
11. Backend calls `POST /ml/recommend` → up to 14 offers ranked against that interest vector
12. Response sent back to frontend with the extracted data, the reward result (`category` + `gemini_category`), the verification verdict (`fraudScore`, `riskLevel`, `anomalyScore`, `anomalyFlag`, `crossUserDuplicate`, `itemsTotalMismatch`) and `recommendedRewards`

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
      ├── forensics.py    → 31 hand-designed forensic features       [BASELINE ONLY — never called, see note]
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

**`forensics.py` is built but deliberately not served.** It computes 31
hand-designed tamper features — Error Level Analysis, noise-residual
consistency, JPEG block alignment, copy-move similarity, local brightness,
local sharpness and saturation — with no learning involved, so a small corpus
barely hurts it. It exists to answer one question: is the CNN's ceiling a
property of the method or of the data? It reaches AUC 0.736 on its own, and
rank-average fusion with the CNN **lowers** the result from 0.805 to 0.790
(0.864 → 0.833 on real receipts); a learned stacker was worse still at 0.758.
The two signals correlate at Spearman ρ = 0.638, so the features add redundancy
plus their own noise. The code stays because the negative result is evidence
that the corpus, not the architecture, is the limit — but nothing in the request
path calls it, because calling it would make the served system worse.

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
