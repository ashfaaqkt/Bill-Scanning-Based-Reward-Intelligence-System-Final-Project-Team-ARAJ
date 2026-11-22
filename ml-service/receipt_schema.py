"""
Response validator for the extraction model's receipt JSON.

v1.0 trusted whatever json.loads returned. This module gives every successful
extraction the same shape, and in particular a `currency` field that is either
an ISO 4217 code or None — never a guess. The ML service does not refuse on
currency; the backend's currency gate (backend/lib/currencyGate.js) is the
single place that decides what is supported.
"""

import re

KNOWN_CODES = {"INR", "SAR", "AED", "QAR", "USD", "KWD", "BHD", "OMR",
               "EUR", "GBP", "MYR", "IDR"}

# Same markers as backend/lib/currency.js — keep the two in step.
_CURRENCY_PATTERNS = [
    ("INR", re.compile(r"₹|\bINR\b|\bRs\.?(?=\s|\d|$)|रु", re.I)),
    ("SAR", re.compile(r"ر\s?\.?\s?س|\bSAR\b|\bSR\b", re.I)),
    ("AED", re.compile(r"د\s?\.?\s?إ|\bAED\b|\bDhs?\b\.?", re.I)),
    ("QAR", re.compile(r"ر\s?\.?\s?ق|\bQAR\b|\bQR\b", re.I)),
    ("USD", re.compile(r"US\$|\$|\bUSD\b", re.I)),
    ("EUR", re.compile(r"€|\bEUR\b", re.I)),
    ("GBP", re.compile(r"£|\bGBP\b", re.I)),
]

_ARABIC_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_ARABIC_DIGITS.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})


def to_latin_digits(value):
    return str(value).translate(_ARABIC_DIGITS)


def detect_currency(text):
    """The single currency marked in `text`, or None (none, or conflicting)."""
    if text is None:
        return None
    s = str(text)
    found = {code for code, pat in _CURRENCY_PATTERNS if pat.search(s)}
    return found.pop() if len(found) == 1 else None


def normalize_currency_code(value):
    """ISO code for a model-supplied currency ("sar", "₹", "ر.س"), or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"[A-Za-z]{3}", s):
        upper = s.upper()
        return upper if upper in KNOWN_CODES else None
    return detect_currency(s)


def validate_receipt_payload(result):
    """Normalise a successful extraction in place and return it.

    Error payloads ({"error": ...}) pass through untouched. For a success:
      * currency   — ISO code from the model's field, else from a marker in the
                     total, else None. Never defaulted.
      * handwritten_flag / handwritten_details — always present (v1.0 rule).
      * items      — always a list.
    """
    if not isinstance(result, dict) or "error" in result:
        return result

    currency = normalize_currency_code(result.get("currency"))
    if currency is None and isinstance(result.get("total"), str):
        currency = detect_currency(to_latin_digits(result["total"]))
    result["currency"] = currency

    result.setdefault("handwritten_flag", False)
    result.setdefault("handwritten_details", None)
    if not isinstance(result.get("items"), list):
        result["items"] = []
    return result
