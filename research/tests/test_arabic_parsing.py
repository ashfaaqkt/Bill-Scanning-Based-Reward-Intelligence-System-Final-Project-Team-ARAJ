"""Arabic currency and date parsing, through the real backend code via js_normalize."""
import json
import os
import subprocess

import pytest

from receipt_schema import detect_currency, normalize_currency_code, validate_receipt_payload

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def normalise(records, supported=None):
    env = dict(os.environ)
    env.pop("SUPPORTED_CURRENCIES", None)
    if supported:
        env["SUPPORTED_CURRENCIES"] = supported
    out = subprocess.run(["node", os.path.join(REPO, "research", "eval", "js_normalize.js"), REPO],
                         input="\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                         capture_output=True, text=True, check=True, env=env)
    return [json.loads(l) for l in out.stdout.splitlines()]


@pytest.mark.parametrize("total, amount, currency", [
    ("١٬٢٣٤٫٥٠ ر.س", 1234.5, "SAR"),
    ("٤٥٫٠٠ د.إ", 45.0, "AED"),
    ("QAR ٩٧٫٩٣", 97.93, "QAR"),
    ("₹ 3,561.13", 3561.13, "INR"),
    ("SAR 1.234,50", 1234.5, "SAR"),
])
def test_amounts(total, amount, currency):
    [r] = normalise([{"total": total, "date": "2026-04-15"}], supported="INR,SAR,AED,QAR")
    assert r["amount"] == pytest.approx(amount)
    assert r["currency"] == currency


@pytest.mark.parametrize("date, iso", [
    ("١٥/٠٤/٢٠٢٦", "2026-04-15"),
    ("٢٠٢٦-٠٩-٠٩", "2026-09-09"),
    ("3 أكتوبر 2026", "2026-10-03"),
    ("١٤ مايو ٢٠٢٦", "2026-05-14"),
    ("7 نيسان 2026", "2026-04-07"),
])
def test_dates(date, iso):
    [r] = normalise([{"total": "₹ 10", "date": date}])
    assert r["date_iso"] == iso


def test_gate_default_is_inr_only():
    rs = normalise([{"total": "٤٥ ر.س", "date": "2026-01-01"}, {"total": "₹ 45", "date": "2026-01-01"}])
    assert rs[0]["gate_status"] == "rejected_currency" and rs[0]["gate_error"] == "UNSUPPORTED_CURRENCY"
    assert rs[1]["gate_status"] == "accepted"


def test_gate_widened_by_env():
    [r] = normalise([{"total": "٤٥ ر.س", "date": "2026-01-01"}], supported="INR,SAR")
    assert r["gate_status"] == "accepted"


def test_python_validator_agrees():
    assert normalize_currency_code("ر.ق") == "QAR"
    assert detect_currency("٢٩٩ د.إ") == "AED"
    assert validate_receipt_payload({"total": "١٠ ر.س"})["currency"] == "SAR"
