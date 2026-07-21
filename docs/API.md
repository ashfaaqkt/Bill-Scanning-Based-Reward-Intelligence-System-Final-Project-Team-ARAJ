# API Reference — Team ARAJ

## Backend (Node.js) — Base URL: http://localhost:3000

### Auth

| Method | Route | Description |
|---|---|---|
| POST | /api/signup | Register new user, returns JWT |
| POST | /api/login | Login, returns JWT + display name |

### Receipts

| Method | Route | Description |
|---|---|---|
| POST | /api/upload | Upload receipt image — triggers OCR + ML pipeline |
| GET | /api/history | List all receipts for authenticated user (newest first) |
| GET | /api/receipt/:id | Get single receipt + line items |

### User

| Method | Route | Description |
|---|---|---|
| GET | /api/user | Returns current point balance and display name |
| GET | /api/analytics | Aggregated spend summary, category chart, insights |

### Rewards

| Method | Route | Description |
|---|---|---|
| GET | /api/claimed-rewards | List all claimed vouchers and scratch cards |
| POST | /api/claim-reward | Claim a reward (atomic point deduction) |

---

## ML Service (Python Flask) — Base URL: http://localhost:5001

### Health

| Method | Route | Description |
|---|---|---|
| GET | /health | Service health check |

### ML Endpoints

| Method | Route | Owner | Description | Wired into `/api/upload`? |
|---|---|---|---|---|
| POST | /ml/ocr | Ashfaaq | Extract structured data from receipt image (Gemini, ocr.py) | ✅ yes |
| POST | /ml/fraud-score | Ranjeet | Return fraud probability score from OCR signals | ✅ yes |
| POST | /ml/update-profile | Arpan | Update user spend interest vector | ✅ yes (fire-and-forget) |
| POST | /ml/classify | Arpan | Classify receipt spend category | ✅ yes (trained; used when confidence ≥ 0.45, else Gemini category) |
| POST | /ml/anomaly | Ranjeet | Detect unusual spending amounts | ❌ not yet (stub) |
| POST | /ml/recommend | Arpan | Return ranked personalised reward recommendations | ❌ not yet (stub) |

### Example: POST /ml/ocr

The backend sends the receipt as base64 (no shared filesystem). The CLI/tests may
send `{ "image_path": "..." }` instead.

Request:
```json
{ "image": "<base64-encoded-image>", "mimeType": "image/jpeg" }
```

Response (success):
```json
{ "rawMerchant": "Reliance Fresh", "date": "2026-04-15", "total": 157.50,
  "category": "Supermarket / Grocery", "items": [{ "name": "Milk", "price": 50.0 }],
  "handwritten_flag": false, "handwritten_details": null }
```

Rejections return HTTP 422 with `{ "error": "unreadable" }` (blur/unreadable) or
`{ "error": "multi_bill_detected" }` (more than one receipt).

### Example: POST /ml/classify

Request:
```json
{ "items_text": "2x Milk, 1x Bread, 3x Eggs", "merchant": "Reliance Fresh" }
```

Response:
```json
{ "category": "Food & Beverage", "confidence": 0.7967, "model_ready": true }
```

Powered by the trained Notebook 02 model (`classifier.pkl` + `tfidf.pkl`, Random Forest). If the
model files are absent, it returns `{ "model_ready": false }` and the backend keeps Gemini's category.
`/api/upload` uses the classifier's category only when `model_ready` **and** `confidence ≥ 0.45`;
otherwise it falls back to the OCR/Gemini category. The upload response includes both the final
`category` and `gemini_category` (plus `ml_confidence` when the classifier was used).

> Served model must be trained in the ml-service venv: `ml-service/.venv/bin/python ml-service/train_classifier.py`
> (matches the serving sklearn version — see ARCHITECTURE.md).

### Example: POST /ml/fraud-score

Request:
```json
{ "ocr_result": { "handwritten_flag": true, "error": null } }
```

Response:
```json
{ "fraud_score": 0.35, "signals": { "blur": false, "duplicate": false, "tamper": true, "handwritten": true, "multi_bill": false } }
```

---

*TODO: Expand each endpoint with full request/response schemas as implementation progresses.*
