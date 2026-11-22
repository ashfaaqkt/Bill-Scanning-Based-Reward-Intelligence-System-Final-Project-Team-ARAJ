"""Currency field in the extraction schema, prompt and response validator.
Run: cd ml-service && .venv/bin/python -m pytest tests/ -q
"""
import json
import types

import numpy as np
import pytest
from PIL import Image

import ocr
from receipt_schema import (detect_currency, normalize_currency_code,
                            to_latin_digits, validate_receipt_payload)


def test_prompt_asks_for_currency_and_forbids_guessing():
    assert '"currency"' in ocr.RECEIPT_PROMPT
    assert "ISO 4217" in ocr.RECEIPT_PROMPT
    assert "return null" in ocr.RECEIPT_PROMPT


@pytest.mark.parametrize("raw, code", [
    ("INR", "INR"), ("sar", "SAR"), (" AED ", "AED"), ("QAR", "QAR"), ("USD", "USD"),
    ("₹", "INR"), ("Rs.", "INR"), ("ر.س", "SAR"), ("د.إ", "AED"), ("ر.ق", "QAR"), ("$", "USD"),
    (None, None), ("", None), ("unknown", None), ("XYZ", None),
])
def test_normalize_currency_code(raw, code):
    assert normalize_currency_code(raw) == code


def test_detect_currency_and_digits():
    assert to_latin_digits("١٢٣٫٥٠") == "123٫50"
    assert detect_currency("١٢٣٫٥٠ ر.س") == "SAR"
    assert detect_currency("1,234.50") is None
    assert detect_currency("SAR 10 AED 10") is None


def test_validator_sets_currency_never_defaults_inr():
    assert validate_receipt_payload({"total": 299})["currency"] is None
    assert validate_receipt_payload({"total": 299, "currency": "inr"})["currency"] == "INR"
    assert validate_receipt_payload({"total": "٢٩٩ ر.س"})["currency"] == "SAR"
    out = validate_receipt_payload({"total": 1})
    assert out["handwritten_flag"] is False and out["handwritten_details"] is None
    assert out["items"] == []


def test_validator_passes_errors_through():
    err = {"error": "unreadable"}
    assert validate_receipt_payload(err) == {"error": "unreadable"}


# ── extract_receipt_data with the model stubbed ──────────────────────────────
@pytest.fixture
def stub_gemini(monkeypatch, tmp_path):
    """Run the real extraction path with a fake client; no network, no key."""
    replies = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            return types.SimpleNamespace(text=json.dumps(replies["body"]), candidates=[])

    monkeypatch.setattr(ocr, "api_key", "test-key")
    monkeypatch.setattr(ocr, "_API_KEYS", [("GEMINI_API_KEY", "test-key")])
    monkeypatch.setitem(ocr._KEY_STATE, "GEMINI_API_KEY",
                        {"client": None, "last_used": 0.0, "cooling_until": 0.0, "unsupported": set()})
    monkeypatch.setattr(ocr, "_client_for", lambda n, v: types.SimpleNamespace(models=FakeModels()))
    monkeypatch.setattr(ocr, "_blur_score", lambda gray: 1000.0)
    monkeypatch.setattr(ocr, "RATE_LIMIT_INTERVAL", 0)

    path = tmp_path / "r.png"
    Image.fromarray(np.full((64, 64, 3), 255, dtype=np.uint8)).save(path)
    return replies, str(path)


def test_extraction_returns_model_currency(stub_gemini):
    replies, path = stub_gemini
    replies["body"] = {"rawMerchant": "Al Baik", "date": "2026-04-15", "total": 45.0,
                       "currency": "SAR", "items": []}
    assert ocr.extract_receipt_data(path)["currency"] == "SAR"


def test_extraction_without_currency_yields_none(stub_gemini):
    replies, path = stub_gemini
    replies["body"] = {"rawMerchant": "Shop", "date": "2026-04-15", "total": 299, "items": []}
    out = ocr.extract_receipt_data(path)
    assert "currency" in out and out["currency"] is None


def test_flask_ocr_route_passes_currency_through(monkeypatch):
    # The ML service reports the currency; it does not enforce the gate.
    import app as ml_app
    monkeypatch.setattr(ml_app.ocr, "extract_receipt_data_from_base64",
                        lambda b64, mime: {"rawMerchant": "X", "total": 10, "currency": "AED", "items": []})
    client = ml_app.app.test_client()
    res = client.post("/ml/ocr", json={"image": "aGVsbG8=", "mimeType": "image/png"})
    assert res.status_code == 200
    assert res.get_json()["currency"] == "AED"


def test_flask_ocr_route_keeps_v1_rejections(monkeypatch):
    import app as ml_app
    monkeypatch.setattr(ml_app.ocr, "extract_receipt_data_from_base64",
                        lambda b64, mime: {"error": "unreadable", "reason": "image_too_blurry"})
    res = ml_app.app.test_client().post("/ml/ocr", json={"image": "aGVsbG8="})
    assert res.status_code == 422
