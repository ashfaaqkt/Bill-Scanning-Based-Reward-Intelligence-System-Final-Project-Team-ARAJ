#!/usr/bin/env python3
"""
Download the trained model binaries into ml-service/models/.

The binaries are gitignored on purpose (see docs/CONTRIBUTING.md — a committed
checkpoint is what made one feature branch unmergeable), so a fresh clone on a
build host has none of them. Without this step the service still starts, and
every model silently falls back to its baseline:

    classifier.py  -> model_ready False, category comes from Gemini instead
    fraud.py       -> 0.05 for every receipt
    anomaly.py     -> 0.05 for every transaction

That is the failure this script exists to prevent, which is why it exits
non-zero on a failed download: better to fail the build loudly than to deploy a
service whose models are quietly dead.

Usage
-----
Run it from the build command, not the start command — the build runs once, the
start command runs on every wake from sleep:

    pip install -r requirements.txt && python fetch_models.py

Configuration
-------------
MODEL_BASE_URL   Base URL the files hang off. Defaults to the v1.0-fyp GitHub
                 release assets. Any static host works — the files are fetched
                 by plain HTTPS GET.
SKIP_MODEL_FETCH Set to 1 to skip entirely (local dev, where models already
                 exist in place).
"""

import hashlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"

DEFAULT_BASE = (
    "https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-"
    "System-Final-Project-Team-ARAJ/releases/download/v1.0-fyp"
)
BASE_URL = os.environ.get("MODEL_BASE_URL", DEFAULT_BASE).rstrip("/")

# (filename, approximate MB, what breaks without it)
REQUIRED = [
    ("tamper_cnn_cv_normalized_448.pt", 8.8, "fraud.py — tamper CNN"),
    ("classifier.pkl", 8.4, "classifier.py — spend category"),
    ("tfidf.pkl", 0.1, "classifier.py — vectoriser"),
    ("spending_anomaly.joblib", 2.4, "anomaly.py — Isolation Forest"),
]

# Optional: present only once Notebook 04 has shipped. A missing collaborative
# filter is a documented, deliberate state — recommend.py ranks content-based
# until it exists — so this must never fail the build.
OPTIONAL = [
    ("collab_filter.pkl", 0.0, "recommend.py — SVD collaborative filter"),
]


def _download(name: str) -> None:
    url = f"{BASE_URL}/{name}"
    target = MODELS_DIR / name
    tmp = target.with_suffix(target.suffix + ".part")

    with urllib.request.urlopen(url, timeout=120) as response:
        if response.status != 200:
            raise urllib.error.HTTPError(url, response.status, "bad status",
                                         response.headers, None)
        tmp.write_bytes(response.read())

    # Rename only after a complete read, so an interrupted download can never
    # leave a truncated file that torch.load would fail on at request time.
    tmp.replace(target)


def fetch(name: str, size_mb: float, used_by: str, required: bool) -> bool:
    target = MODELS_DIR / name
    if target.exists() and target.stat().st_size > 0:
        actual = target.stat().st_size / 1_048_576
        print(f"  = {name:38s} already present ({actual:.1f} MB)")
        return True

    print(f"  > {name:38s} downloading (~{size_mb:.1f} MB) — {used_by}")
    try:
        _download(name)
    except Exception as exc:                      # noqa: BLE001 — report anything
        (MODELS_DIR / (name + ".part")).unlink(missing_ok=True)
        level = "ERROR" if required else "note"
        print(f"    {level}: {exc}")
        return not required

    actual = target.stat().st_size / 1_048_576
    print(f"    ok — {actual:.1f} MB")
    return True


def main() -> int:
    if os.environ.get("SKIP_MODEL_FETCH") == "1":
        print("fetch_models: SKIP_MODEL_FETCH=1 — skipping.")
        return 0

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"fetch_models: target {MODELS_DIR}")
    print(f"fetch_models: source {BASE_URL}")

    ok = True
    for name, size_mb, used_by in REQUIRED:
        ok &= fetch(name, size_mb, used_by, required=True)
    for name, size_mb, used_by in OPTIONAL:
        fetch(name, size_mb, used_by, required=False)

    if not ok:
        print(
            "\nfetch_models: FAILED — one or more required models are missing.\n"
            "The service would start but every model would return its baseline,\n"
            "so the build is failed deliberately rather than deploying a dead\n"
            "pipeline. Check that MODEL_BASE_URL is reachable and that the\n"
            "release assets are attached and public.",
            file=sys.stderr,
        )
        return 1

    print("fetch_models: all required models present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
