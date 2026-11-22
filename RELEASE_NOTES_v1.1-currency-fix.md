# v1.1 — currency fix

A maintenance change on top of the submitted `v1.0-fyp`. That tag is unchanged
and still marks the submitted system. **This change is not tagged.**

## What was wrong

The pipeline only understood INR written in Latin digits, and it never said so:

- `sanitizeCurrencyValue` removed a fixed list of INR-style symbols and **every
  comma**, then called `parseFloat`. `"١٢٣٫٥٠ ر.س"` parsed to `0`, and
  `"1.234,50"` parsed to `1.2345`.
- `normalizeReceiptDate` handled only Latin digits and English month names. It
  read every numeric date as day-first, so `04/15/2026` came out as the
  impossible `2026-15-04`, and it never checked that the date existed
  (`31/02/2026` came out as `2026-02-31`).
- The extraction schema had no `currency` field. Every receipt was implicitly
  INR, and the points formula (₹100 = 1 point), the anomaly reference
  (`POPULATION_REFERENCE_INR`) and the offer catalogue priced it that way.

## What changed

| Area | Change |
|---|---|
| `ml-service/ocr.py` | The prompt asks for `currency` (ISO 4217 or `null`) and says to infer it only from a printed symbol or unambiguous country evidence (GSTIN, +91 → INR), never to guess |
| `ml-service/receipt_schema.py` (new) | Validates every successful extraction. `currency` is always present, as an ISO code or `None`, and never defaults to INR |
| `backend/lib/currency.js` (new) | `parseAmount` returns `{ amount, currency }`. Handles ₹ / Rs. / INR, ر.س / SAR, د.إ / AED, ر.ق / QAR, $, Eastern Arabic and Persian digits, ٫ and ٬, and both 1,234.50 and 1.234,50. `sanitizeCurrencyValue` keeps its v1.0 contract (a number, or 0) |
| `backend/lib/dates.js` (new) | Eastern Arabic digits, Arabic month names (Gulf/Egyptian and Levantine), bidi marks, trailing times. Dates are calendar-checked. **Day/month rule:** first field > 12 → it is the day; else second field > 12 → it is the day; else **day-first**, which is the convention in India and the Gulf and what v1.0 always did. Hijri dates (marked هـ, or any year before 1900) return `null` rather than being misread |
| `backend/lib/currencyGate.js` (new) | `requireSupportedCurrency` middleware, driven by `SUPPORTED_CURRENCIES` (default `INR`) |
| `backend/server.js` | `/api/upload` is now three stages: extraction → currency gate → the v1.0 pipeline, unchanged. Accepted receipts are stored with `currency`. Exports `app` for tests and listens only when run directly |
| `frontend/public/script.js` | Shows a plain explanation for both currency refusals, instead of a raw code |

## The currency gate

After extraction and **before any Firestore read or write, any ML scoring, or
any reward**:

- A currency in `SUPPORTED_CURRENCIES` (default `INR`) proceeds.
- Any other currency returns HTTP 422:
  `{ "error": "UNSUPPORTED_CURRENCY", "message": "Only INR receipts are supported.", "detectedCurrency": "SAR", "supportedCurrencies": ["INR"] }`
- No detectable currency returns HTTP 422 with `"error": "CURRENCY_NOT_DETECTED"`
  and `"detectedCurrency": null`.

The gate is enforced in exactly one place, the backend. The ML service reports
the currency but never refuses on it.

## Tests

New in this change. Neither tier had an automated suite before.

- `cd backend && npm test`: 26 tests with Node's built-in runner, no new
  dependencies. They cover amount and date parsing, including Arabic, the gate
  middleware, and `POST /api/upload` end to end against a stub ML service and a
  Firestore handle that records every call. For SAR, AED, QAR, USD and a missing
  currency, the upload returns 422 with **zero Firestore calls and no ML call
  after OCR**. INR passes the gate and reaches the pipeline.
- `cd ml-service && .venv/bin/python -m pytest tests/ -q`: 23 tests for the
  prompt, the validator, extraction with the model stubbed, and the Flask OCR
  route.
- `ml-service/test_fraud.py` (v1.0) still passes.

**Not measured:** how often the live extraction model returns `currency: null`
for genuine Indian receipts that print no ₹ symbol. Those receipts would now be
refused with `CURRENCY_NOT_DETECTED`. The prompt tells the model to infer INR
from a GSTIN, a +91 number or an Indian address, but nobody has run it against
the 100 real receipts. Do that before relying on this in production.

## Deploying

**Deploy the ML service before the backend.** A backend with the gate in front
of an ML service still running the v1.0 prompt receives no `currency` field.
Every total arrives as a bare number, so every upload would be refused with
`CURRENCY_NOT_DETECTED`.

No new environment variables are required. `SUPPORTED_CURRENCIES` defaults to
`INR`.
