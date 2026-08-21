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
| GET | /api/recommendations | Reward offers ranked for this user (`?top_n=1..12`, default 6) |

**GET /api/recommendations** proxies `/ml/recommend`. It returns
`{ recommendations[], personalised, model }`. When the ML service is unreachable it
returns an empty list with `model: "unavailable"` rather than an error, so the
frontend falls back to its own static pool. `POST /api/upload` also returns the
same ranked offers as `data.recommendedRewards`.

**POST /api/upload — verification fields.** Alongside the extracted receipt, the
response carries the verdict from the fraud and anomaly models. These are always
present: if the ML service is unreachable the route falls back to a 0.05 baseline
and `"Low"` rather than omitting them.

| Field | Type | Meaning |
|---|---|---|
| `fraudScore` | 0–1 | **Composite** score: OCR signals + perceptual-hash duplicate (+0.40) + 448px CNN when it clears 0.50 (+0.40) |
| `tamperProbability` | 0–1 \| null | What the CNN alone returned. Distinct from `fraudScore`; null when no image reached the scorer |
| `riskLevel` | `Low` \| `Medium` \| `High` | Banded from `fraudScore` (>0.7 High, >0.3 Medium), then escalated by the rules below |
| `anomalyScore` | 0–1 | Isolation Forest score for the amount |
| `anomalyFlag` | bool | True when the amount is an outlier for this user/category |
| `crossUserDuplicate` | bool | Always `false` in a 200 response — that case is now rejected with 409 before scoring (see below) |
| `itemsTotalMismatch` | bool | Line items do not sum to the printed total |
| `fraudSignals` | object | Which signals fired: `blur`, `duplicate`, `tamper`, `handwritten`, `multi_bill` |

Escalation order, applied after the model score: an items/total mismatch raises
`Low` to `Medium`; an anomaly flag raises `Low` to `Medium`. The booleans and
`fraudSignals` exist so the client can state *why* a receipt was flagged instead
of showing an unexplained number — the web client renders every signal that fired
in the verification block of the results panel.

**409 responses carry a `code`.** `ALREADY_CLAIMED` means the same physical
receipt has already been claimed on a different account: it is rejected before
scoring, no points are awarded and no receipt is written, and the attempt is
logged to `Fraud_Scores` with `blocked: true`, the fingerprint, and which claim
won. A 409 without that code is an ordinary duplicate of the caller's own
receipt (exact fingerprint or fuzzy merchant match).

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
| POST | /ml/update-profile | Arpan | Update user spend interest vector | ✅ yes (awaited, so recommendations see the new receipt) |
| POST | /ml/classify | Arpan | Classify receipt spend category | ✅ yes (trained; used when confidence ≥ 0.65, else Gemini category) |
| POST | /ml/anomaly | Ranjeet | Detect unusual spending amounts | ✅ yes — trained Isolation Forest (FPR 13.2%); returns `anomaly_score`, `is_anomaly`, `reference_basis` |
| POST | /ml/recommend | Arpan | Return ranked personalised reward recommendations | ✅ yes — content-based ranking; also exposed as `GET /api/recommendations` |

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
`/api/upload` uses the classifier's category only when `model_ready` **and** `confidence ≥ 0.65`;
otherwise it falls back to the OCR/Gemini category. The upload response includes both the final
`category` and `gemini_category` (plus `ml_confidence` when the classifier was used).

> Served model must be trained in the ml-service venv: `ml-service/.venv/bin/python ml-service/train_classifier.py`
> (matches the serving sklearn version — see ARCHITECTURE.md).

### Example: POST /ml/fraud-score

Request. `image` and `known_hashes` are both optional but the check degrades
without them: no image means the tamper CNN and the perceptual hash are skipped
entirely, and no hashes means the duplicate check has nothing to compare against
and always returns false.
```json
{
  "ocr_result": { "handwritten_flag": true, "error": null },
  "image": "<base64>",
  "mimeType": "image/jpeg",
  "known_hashes": ["d4d069ec7871e538"]
}
```

Response:
```json
{
  "fraud_score": 0.35,
  "signals": { "blur": false, "duplicate": false, "tamper": true, "handwritten": true, "multi_bill": false },
  "tamper_probability": 0.4631,
  "image_phash": "d4d069ec7871e538"
}
```

`image_phash` is returned so the caller can **store** it — `server.js` writes it
to the receipt document and sends the last 300 back on the next upload. Without
that loop the duplicate signal can never fire.

---

### Example: POST /ml/anomaly

Request:
```json
{ "user_id": "abc123", "amount": 4500.0, "category": "Supermarket / Grocery", "date": "2026-08-07" }
```

Response:
```json
{ "anomaly_score": 0.5152, "is_anomaly": true, "reference_basis": "population" }
```

`reference_basis` is `"user"` once the user has 5+ receipts (their own median is
used), otherwise `"population"`. The check is one-sided — only amounts *above* the
reference can be flagged. Falls back to `{"anomaly_score": 0.05, "is_anomaly": false}`
when the model file is absent.

### Example: POST /ml/recommend

Request:
```json
{ "user_id": "abc123", "top_n": 5 }
```

Response:
```json
{
  "recommendations": [
    { "id": "bigbasket", "icon": "🛒", "title": "BigBasket Voucher",
      "offer": "Flat ₹150 OFF on groceries", "category": "grocery",
      "score": 0.963, "reason": "matches 100% of your recent spend" }
  ],
  "personalised": true,
  "receipts_seen": 3,
  "interest": { "grocery": 1.0 },
  "model": "content-based"
}
```

`model` is `"content-based"` until the NB 04 collaborative filter ships, at which
point it becomes `"collaborative+content"`. `personalised` is false for users with
fewer than 2 receipts, who receive the catalogue in popularity order.
