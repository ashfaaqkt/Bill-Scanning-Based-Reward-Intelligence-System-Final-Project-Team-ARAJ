# Local Setup Guide — Team ARAJ

> **You may not need any of this.** The system is deployed and live at
> **[araj-capstone.vercel.app](https://araj-capstone.vercel.app)** — sign up and
> upload a receipt. This guide is for running it on your own machine, for
> development, retraining or offline demonstration.
>
> Live services: web client on Vercel, backend on Render
> (`https://araj-backend.onrender.com`), ML service on Google Cloud Run
> (`https://araj-ml-service-1012478382071.asia-southeast1.run.app`). Topology and
> why it is split three ways: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Prerequisites

- Node.js 20+
- Python 3.10+
- Firebase project with Firestore enabled
- Google Gemini API key

---

## 1. Clone the repo

```bash
git clone https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-Final-Project-Team-ARAJ
cd Bill-Scanning-Based-Reward-Intelligence-System-Final-Project-Team-ARAJ
```

---

## 2. Backend (Node.js)

```bash
cd backend
npm install

# Copy and fill in your environment variables
cp .env.example .env
# Edit .env with your Firebase project ID and JWT secret.
# NOTE: OCR now runs in the ML service, so the backend no longer needs GEMINI_API_KEY —
# the Gemini key goes in ml-service/.env (see step 3). The backend forwards uploads to
# /ml/ocr, so the ML service (step 3) MUST be running for /api/upload to work.

# Place your Firebase service account JSON at:
# backend/serviceAccountKey.json  (never commit this file)

node server.js
# Server runs on http://localhost:3000
```

---

## 3. ML Service (Python Flask)

```bash
cd ml-service
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create ml-service/.env with your Gemini key(s) — ocr.py reads them:
#   GEMINI_API_KEY_1=your_key_here
#
# One key is enough to run. ocr.py accepts GEMINI_API_KEY_1..N and rotates over
# them, because the free tier's 5 requests/minute is PER PROJECT — keys from
# separate projects multiply the ceiling. A bare GEMINI_API_KEY still works.
#
# If a key is on a billed plan, name it so it is tried first and skips the
# 23-second free-tier spacing:
#   GEMINI_PAID_KEYS=GEMINI_API_KEY_1
#
# Billing removes 429 quota errors. It does NOT remove 503 "model overloaded" —
# that is Google's shared capacity. ocr.py handles it by rotating across both
# keys and models and cooling a model that 503s for 120s.

python app.py
# ML service runs on http://localhost:5001
# Must be running before the backend can process /api/upload (OCR lives here).
```

---

## 4. Frontend

Open `frontend/index.html` in a browser, or serve with any static server:

```bash
cd frontend
npx serve .
```

---

## 5. Running Notebooks

```bash
# (optional) regenerate the cleaned, train-ready CSVs first — no training happens here
python dataset/prepare_dataset.py

cd notebooks
jupyter notebook
```

`receipts_master.csv` is already populated (CORD + SROIE), so Notebooks 01, 02, 04, 05 run on
the CSVs alone. Notebook 03 (fraud CNN) additionally needs the receipt **images** downloaded
from Drive into `dataset/tampered/` and `dataset/indian/`. See `dataset/DATA_PREP.md`.

**All five notebooks are committed with outputs** (04 and 05 landed 19 Aug 2026).
Executed code cells per notebook, counted from the committed `.ipynb`:

| Notebook | Code cells | With outputs |
|---|---|---|
| 01 data exploration | 11 | 11 |
| 02 category classifier | 9 | 7 |
| 03 fraud detection | 13 | 13 |
| 04 collaborative filter | 4 | 4 |
| 05 reward engine | 4 | 3 |

The gaps in 02 and 05 are cells that write artefacts rather than produce a
result; every figure and metric quoted in the report comes from a cell that does
carry its output.

---

## 6. Rebuilding the models

Model binaries are gitignored, so a fresh clone has none. Everything is reproducible
from the data in the repo (plus the images from Drive for the fraud CNN):

```bash
# ── data preparation — run in this order ──
python3 dataset/flatten_images.py        # Drive folders arrive nested; flatten them
python3 dataset/rasterize_pdfs.py        # 23 PDFs → JPG (19 are genuine — skipping this
                                         #   silently drops a third of the minority class)
python3 dataset/normalize_images.py      # identical re-encode; removes the JPEG shortcut
python3 dataset/repair_master_schema.py  # adds total_parsed / currency / spend_category / fraud_label

# ── models ──
ml-service/.venv/bin/python ml-service/train_classifier.py            # category classifier
ml-service/.venv/bin/python ml-service/train_anomaly.py               # anomaly (compares IF / OC-SVM / LOF)
python ml-service/train_fraud_cv.py --normalized --img-size 448       # fraud CNN, ~40 min on Apple MPS

# ── evaluation extras (optional) ──
python ml-service/train_fraud_forensics.py --normalized               # forensic-feature baseline
python ml-service/train_fraud_fusion.py --normalized --img-size 448   # fusion ablation
python ml-service/make_report_figures.py                              # regenerate report/assets/fig_*.png
```

**Two things that will bite you:**

- **Train the *served* models with `ml-service/.venv`.** The notebook env (Python 3.9,
  sklearn 1.5.x) and the serving env (3.13, sklearn 1.8.x) differ, and a model pickled by
  one raises `InconsistentVersionWarning` in the other.
- **The fraud CNN must be served at the resolution it was trained at.** `fraud.py` uses a
  single `IMG_SIZE` constant for both; serving a 448-trained model at 224 silently degrades
  every prediction rather than failing loudly.

The fraud CNN no longer needs Colab — it trains locally on Apple MPS.

---

## Environment Variables Reference

See `backend/.env.example` for all required variables and descriptions.

---

## Team Member Implementation Guide

Each team member owns specific modules. Here's what each person should implement:

### Ashfaaq Feroz Muhammad (Lead Dev + Chief Editor)
**Primary Responsibility:** Frontend UI/UX, OCR Pipeline & ML Integration, Backend API coordination, Project Lead

**Development Work (Code Implementation):**

**Frontend & Backend:**
- `frontend/public/index.html` — Complete landing page, auth UI, dashboard layout
- `frontend/public/style.css` — Responsive styling for all pages
- `frontend/public/script.js` — Form validation, API calls, UI interactions, error handling
- `backend/server.js` — Express server setup, route handlers, Firebase Admin integration, API orchestration
- Authentication system — JWT middleware, signup/login endpoints, token validation

**ML Service - OCR Pipeline (Gemini Integration):**
- `ml-service/app.py` — Flask microservice skeleton with `/ml/classify` and `/ml/fraud-score` endpoints
- **Base OCR Script** — Accept receipt image input, call Gemini API, return JSON with extracted data
- **Sharpness gate** — contrast-normalised sharpness measured over the ink only, below 40 returns 422
  (`IMAGE_TOO_BLURRY`). Replaced a whole-frame Laplacian variance < 100 on 20 Aug, which was an
  edge-energy *density* rather than a focus measure and refused 12 of 100 real receipts.
  Re-check with `ml-service/calibrate_blur_gate.py --scan` (no API calls)
- **Multi-Bill Detection** — Text region count + layout analysis (returns 422 Multi-bill error if detected)
- **Handwritten Modification Detection** — Check Gemini confidence score + text region density anomaly
- **Integration with Fraud Detection** — Call fraud_detector.py from `/api/upload` route, replace hardcoded scores with real fraud_score

**Key Implementation Tasks (12-Day Battle Plan):**
1. Build responsive, accessible frontend UI with form validations
2. Implement complete authentication flow (Firebase Auth + JWT)
3. **Day 2:** Write base OCR script using Gemini API (test on 5 bills)
4. **Day 3:** Add blur detection to OCR using OpenCV
5. **Day 4:** Create Flask microservice skeleton with `/ml/classify` and `/ml/fraud-score` endpoints
6. **Day 5:** Add multi-bill detection logic to OCR
7. **Day 6:** Add handwritten modification detection to OCR
8. **Day 8:** Integrate fraud_detector.py into server.js `/api/upload` route
9. **Day 9:** End-to-end system test: upload receipt → OCR → fraud score → points calculation
10. Create backend routes that properly call ML service endpoints

**Leadership Duties (PR Review & Merge):**
- Review all PRs from team members before merging to `dev`
- Ensure code quality and consistency
- Merge `dev` → `main` only when ready for production
- **Day 10:** Final integration sync - merge all branches, run full system test
- **Day 11:** Clean up GitHub repo, update README, tag release as v0.2-dataset-ocr-fraud
- **Day 12:** Final repo push, lead presentation, explain all architecture decisions
- Coordinate with team on API contracts and specifications

---

### Arpan Chatterjee (ML Research + Dataset)
**Primary Responsibility:** Receipt Classification, User Profiling, Reward Logic

**Files to Work On:**
- `ml-service/classifier.py` — Implement TF-IDF + Random Forest category classification
- `ml-service/user_profile.py` — Update user interest vectors based on receipt history
- `ml-service/recommend.py` — Implement reward recommendation ranking logic
- `dataset/processed/` — Manage and validate CSV datasets

**Key Implementation Tasks:**
1. Train and validate classifier on CORD/SROIE receipt dataset
2. Maintain the per-user interest vector as receipts arrive — a **decayed
   weighting over categories already seen**, recomputed per upload. This is not
   online learning and must not be described as such: every model in this system
   is a static file loaded at startup, uploads run inference only, and no user
   image is retained. Retraining is a manual step (the notebooks or `train_*.py`)
3. Design reward ranking algorithm (collaborative filtering + content-based)
4. Document model performance and accuracy metrics

---

### Ranjeet Singh (Fraud Detection + Testing)
**Primary Responsibility:** Fraud Detection, System Testing, Quality Assurance

**Files to Work On:**
- Test suites and validation scripts
- 3 demo receipts (clean / blurry / tampered) for the viva

**Status (Aug 23, 2026):** `fraud.py`, `anomaly.py` and the `/ml/fraud-score` +
`/ml/anomaly` endpoints are **implemented and live** — tamper CNN (AUC 0.805),
perceptual-hash duplicates, and a trained Isolation Forest (FPR 13.2%). See
[`report/model_cards/`](../report/model_cards/README.md).

**Closed since:**
- **End-to-end test through the live stack** — closed 19 Aug. The full chain ran
  against live Firestore and live Gemini through `POST /api/upload`. That run is
  what exposed the two dead seams (the tamper CNN never received the image; no
  perceptual hash was ever stored).
- **TC-26, the browser run** — closed 21 Aug. Six receipts in one session, three
  genuine across three categories plus one tampered, one blurred and one
  containing two bills. Every case behaved as specified, including both refusals.
- **The 3 demo receipts** — captured in the same session.

**Remaining:**
1. Regression test suite covering all backend + ML routes (de-scoped at the
   Aug 12 freeze; the whole-stack sessions carried the verification instead)

---

### Jyoti Kataria (Data + Docs)
**Primary Responsibility:** Dataset Management, Documentation, Data Pipeline

**Files to Work On:**
- `dataset/` — Manage genuine, tampered, Indian receipt datasets
- `dataset/processed/labels.csv` — Dataset labeling and validation
- `docs/` — API.md, ARCHITECTURE.md, CONTRIBUTING.md
- `notebooks/` — Jupyter notebooks for exploration and analysis

**Key Implementation Tasks:**
1. Organize and validate all receipt images (create `.gitkeep` files for large folders)
2. Document dataset schema and labeling guidelines in `labels.csv`
3. Create Jupyter notebooks for:
   - Data exploration (01_data_exploration.ipynb)
   - Category classifier validation (02_category_classifier.ipynb)
   - Fraud detection analysis (03_fraud_detection.ipynb)
   - Collaborative filtering research (04_collaborative_filter.ipynb)
   - Reward engine design (05_reward_engine.ipynb)
4. Maintain accurate architecture and API documentation

---

## Workflow & Communication

1. **Branch Strategy:**
   - `main` — Stable, production-ready code (Ashfaaq merges only)
   - `dev` — Integration branch, daily syncs
   - `<name>/feature-name` — Individual feature branches:
     - `ashfaaq/ml-integration` — backend, OCR, ML integration, frontend
     - `arpan/classifier` — category classifier, collaborative filter, dataset
     - `ranjeet/fraud-testing` — fraud detection, tampered dataset, QA
     - `jyoti/data-docs` — labelling, dataset docs, reporting

   `main` and `dev` are shared branches, not personal workspaces. Everyone —
   Ashfaaq included — works on their own feature branch and reaches `dev` by PR.

2. **Daily Standup:** 
   - Push changes to your branch by 9pm
   - Update README in your branch with progress

3. **Integration:**
   - Backend (Ashfaaq) coordinates API contracts
   - ML service (Arpan, Ranjeet, Jyoti) ensures endpoints match specs
   - All changes tested locally before pushing

4. **Code Review:**
   - Create PR with clear description of changes
   - Get review from another team member before merging to `dev`
   - Only Ashfaaq merges `dev` → `main`
