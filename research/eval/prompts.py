"""
Prompt ablations for the extraction model (live runs only — a stubbed model
ignores its prompt, so these cannot be measured in a dry run).

  no_schema           free-form request, no JSON schema
  schema_no_currency  the v1.1 schema with the currency field and guidance removed
  schema_currency     the v1.1 prompt as shipped on main
  arabic_hints        schema_currency plus Arabic-specific reading guidance
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml-service"))

_BASE_HEAD = (
    "Analyze this image carefully. "
    "1. Detect the number of receipts. If there is more than one receipt in the image, return exactly: {\"error\": \"multi_bill_detected\"}. "
    "2. Check for any handwritten modifications (e.g., changes to price, date, or merchant name). "
    "3. If the image is blurry or unreadable, return exactly: {\"error\": \"unreadable\"}. "
    "4. Otherwise, extract the following details into a strict JSON format: "
)
_FIELDS_NO_CURRENCY = (
    "{"
    "\"rawMerchant\": \"string\", "
    "\"date\": \"string (YYYY-MM-DD)\", "
    "\"total\": number, "
    "\"category\": \"string ('Supermarket / Grocery', 'Food & Beverage', or 'General Retail')\", "
    "\"items\": [{ \"name\": \"string\", \"price\": number }], "
    "\"handwritten_flag\": boolean, "
    "\"handwritten_details\": \"string or null\""
    "}"
)


def _shipped_prompt():
    from importlib import util
    spec = util.spec_from_file_location(
        "_main_ocr_prompt",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml-service", "ocr.py"))
    # Read the constant without importing the module (which needs the SDK).
    src = open(spec.origin, encoding="utf-8").read()
    start = src.index("RECEIPT_PROMPT = (")
    end = src.index("\n)\n", start) + 2
    ns = {}
    exec(src[start:end], ns)
    return ns["RECEIPT_PROMPT"]


ARABIC_HINTS = (
    " Arabic receipts: text runs right to left, but numbers read left to right. Digits may be "
    "Eastern Arabic (٠١٢٣٤٥٦٧٨٩); convert them to 0-9. ٫ is the decimal point and ٬ groups "
    "thousands. Month names may be Arabic (يناير … ديسمبر, or Levantine كانون الثاني, شباط, …). "
    "Dates are day-first unless the day is impossible. If a date is marked هـ it is Hijri: "
    "return it as printed rather than converting it. The total is usually labelled الإجمالي or "
    "المجموع, and VAT appears as ضريبة القيمة المضافة."
)

VARIANTS = {
    "no_schema": ("Read this receipt and return a JSON object with the merchant name, the date, "
                  "the total amount and the currency."),
    "schema_no_currency": _BASE_HEAD + _FIELDS_NO_CURRENCY,
    "schema_currency": _shipped_prompt(),
    "arabic_hints": _shipped_prompt() + ARABIC_HINTS,
}

_KEY_ALIASES = {
    "rawMerchant": ("rawMerchant", "merchant", "merchant_name", "store", "store_name", "vendor"),
    "date": ("date", "receipt_date", "transaction_date"),
    "total": ("total", "total_amount", "amount", "grand_total"),
    "currency": ("currency", "currency_code"),
}


def coerce_keys(result):
    """Map a free-form (no_schema) reply onto the pipeline's field names."""
    if not isinstance(result, dict) or "error" in result:
        return result
    out = dict(result)
    for target, aliases in _KEY_ALIASES.items():
        for a in aliases:
            if a in result and result[a] not in (None, ""):
                out[target] = result[a]
                break
    return out
