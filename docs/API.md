# API Reference — Team ARAJ

## Backend (Node.js) — Base URL: http://localhost:3000

### Auth

| Method | Route | Description |
|---|---|---|
| POST | /auth/register | Register new user |
| POST | /auth/login | Login, returns JWT |

### Receipts

| Method | Route | Description |
|---|---|---|
| POST | /upload | Upload receipt image, triggers OCR + ML pipeline |
| GET | /receipts | List receipts for authenticated user |
| GET | /receipts/:id | Get single receipt details |

### Rewards

| Method | Route | Description |
|---|---|---|
| GET | /rewards | Get reward recommendations for user |
| GET | /rewards/history | Get past reward events |

---

## ML Service (Python Flask) — Base URL: http://localhost:5001

### Health

| Method | Route | Description |
|---|---|---|
| GET | /health | Service health check |

### ML Endpoints

| Method | Route | Owner | Description |
|---|---|---|---|
| POST | /ml/classify | Arpan | Classify receipt category |
| POST | /ml/fraud-score | Ranjeet | Return fraud probability score |
| POST | /ml/anomaly | Ranjeet | Detect spending anomalies |
| POST | /ml/update-profile | Arpan | Update user interest vector |
| POST | /ml/recommend | Arpan | Return ranked reward recommendations |

### Example: POST /ml/classify

Request:
```json
{ "items_text": "2x Milk, 1x Bread, 3x Eggs", "merchant": "Reliance Fresh" }
```

Response:
```json
{ "category": "Groceries", "confidence": 0.91 }
```

### Example: POST /ml/fraud-score

Request:
```json
{ "image_path": "uploads/receipt_001.jpg", "metadata": { "total": 450.00 } }
```

Response:
```json
{ "fraud_score": 0.12, "signals": { "blur": false, "duplicate": false, "tamper": false } }
```

---

*TODO: Expand each endpoint with full request/response schemas as implementation progresses.*
