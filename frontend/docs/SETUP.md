# Local Setup Guide — Team ARAJ

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
# Edit .env with your Gemini API key, Firebase project ID, and JWT secret

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

python app.py
# ML service runs on http://localhost:5001
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
cd notebooks
jupyter notebook
```

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
- **Blur Detection** — OpenCV Laplacian variance check (< 100 returns 422 Unprocessable error)
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
2. Implement online learning for user profile updates
3. Design reward ranking algorithm (collaborative filtering + content-based)
4. Document model performance and accuracy metrics

---

### Ranjeet Singh (Fraud Detection + Testing)
**Primary Responsibility:** Fraud Detection, System Testing, Quality Assurance

**Files to Work On:**
- `ml-service/fraud.py` — Implement blur detection, duplicate detection, tamper CNN
- `ml-service/anomaly.py` — Implement Isolation Forest for spending anomalies
- `ml-service/app.py` — Wire up `/ml/fraud-score` and `/ml/anomaly` endpoints
- Test suites and validation scripts

**Key Implementation Tasks:**
1. Build robust fraud detection pipeline (image analysis + metadata validation)
2. Train CNN model for receipt tampering detection
3. Implement anomaly detection for suspicious spending patterns
4. Create comprehensive test suite for all ML routes

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
   - `<name>/feature-name` — Individual feature branches

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
