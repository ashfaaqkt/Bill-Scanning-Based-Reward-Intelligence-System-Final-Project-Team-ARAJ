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
