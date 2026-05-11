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

| Method | Route | Owner | Description |
|---|---|---|---|
| POST | /ml/ocr | Ashfaaq | Extract structured data from receipt image |
| POST | /ml/classify | Arpan | Classify receipt spend category |
| POST | /ml/fraud-score | Ranjeet | Return fraud probability score from OCR signals |
| POST | /ml/anomaly | Ranjeet | Detect unusual spending amounts |
| POST | /ml/update-profile | Arpan | Update user spend interest vector |
| POST | /ml/recommend | Arpan | Return ranked personalised reward recommendations |

### Example: POST /ml/classify

Request:
```json
{ "items_text": "2x Milk, 1x Bread, 3x Eggs", "merchant": "Reliance Fresh" }
```

Response:
```json
{ "category": "Supermarket / Grocery", "confidence": 0.91, "model_ready": true }
```

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
