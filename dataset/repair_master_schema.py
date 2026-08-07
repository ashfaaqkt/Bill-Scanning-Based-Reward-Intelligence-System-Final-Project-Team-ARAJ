#!/usr/bin/env python3
"""
Repair the two schema defects that Notebook 01 identified in receipts_master.csv.

1. `total` is not numeric. It mixes currencies and decimal conventions, so a naive
   float() silently drops 724 of 1,762 values (41%). The convention is recoverable
   from the source dataset:

     CORD  -> Indonesian receipts, amounts in IDR. Both '.' and ',' are THOUSANDS
              separators, so '48.000' is 48000 and '1,591,600' is 1591600.
     SROIE -> Malaysian receipts, amounts in MYR. '.' is a real decimal point and
              ',' is a thousands separator, so '$8.20' is 8.20.

2. `category` holds two unrelated taxonomies at once — spend classes (retail,
   restaurant) and fraud labels (genuine, tampered, multi_bill, handwritten).
   Anything reading it naively trains on a meaningless 6-class target.

Both fixes are ADDITIVE: four new columns are appended and every original column is
left untouched, so existing readers keep working. Idempotent — safe to re-run.

Run:  python3 dataset/repair_master_schema.py
"""

import csv
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER = REPO_ROOT / "dataset" / "processed" / "receipts_master.csv"

CURRENCY_BY_SOURCE = {"CORD": "IDR", "SROIE": "MYR"}
SPEND_CLASSES = {"retail", "restaurant"}
FRAUD_CLASSES = {"genuine", "tampered", "multi_bill", "handwritten"}

NEW_COLUMNS = ["total_parsed", "currency", "spend_category", "fraud_label"]


def parse_total(raw, source):
    """
    Returns a float amount in the source's own currency, or None if unrecoverable.
    The currency is NOT converted — mixing IDR and MYR into one number would be
    meaningless without exchange rates, so `currency` is recorded alongside.
    """
    text = str(raw or "").strip()
    if not text:
        return None

    # Currency markers sit flush against the digits ("RM4.00"), so there is no
    # word boundary to anchor on, and some rows carry a label ("TOTAL 47,499").
    # Pull out the last number-shaped token instead of scrubbing the string.
    tokens = re.findall(r"\d[\d.,]*", text)
    if not tokens:
        return None
    token = tokens[-1].rstrip(".,")

    try:
        if source == "CORD":
            # IDR is quoted without minor units; every separator is a thousands mark.
            return float(re.sub(r"[.,]", "", token))
        # MYR: strip thousands commas, keep the decimal point.
        return float(token.replace(",", ""))
    except ValueError:
        return None


def split_category(value):
    """Returns (spend_category, fraud_label) — exactly one is populated."""
    label = str(value or "").strip().lower()
    if label in SPEND_CLASSES:
        return label, ""
    if label in FRAUD_CLASSES:
        return "", label
    return "", ""


def main():
    if not MASTER.exists():
        sys.exit(f"Not found: {MASTER}")

    with open(MASTER, newline="") as handle:
        reader = csv.DictReader(handle)
        original_columns = [c for c in reader.fieldnames if c not in NEW_COLUMNS]
        rows = list(reader)

    parsed_ok = parsed_fail = 0
    spend_count = fraud_count = 0

    for row in rows:
        source = row.get("source", "")
        amount = parse_total(row.get("total"), source)

        if str(row.get("total") or "").strip():
            if amount is None:
                parsed_fail += 1
            else:
                parsed_ok += 1

        row["total_parsed"] = "" if amount is None else f"{amount:.2f}"
        row["currency"] = CURRENCY_BY_SOURCE.get(source, "")

        spend, fraud = split_category(row.get("category"))
        row["spend_category"], row["fraud_label"] = spend, fraud
        spend_count += bool(spend)
        fraud_count += bool(fraud)

    # Only ever back up the pristine file — re-running must not clobber it.
    backup = MASTER.with_suffix(".csv.orig")
    if not backup.exists():
        shutil.copy(MASTER, backup)
    with open(MASTER, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=original_columns + NEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    non_empty = parsed_ok + parsed_fail
    print(f"receipts_master.csv — {len(rows)} rows, backup at {MASTER.name}.orig\n")
    print("Fix 1 — total parsing (per-source currency convention)")
    print(f"  non-empty totals   : {non_empty}")
    print(f"  parsed             : {parsed_ok}  ({parsed_ok / non_empty:.1%})")
    print(f"  still unrecoverable: {parsed_fail}")
    print(f"  baseline float()   : 1038  (58.9%) — for comparison\n")
    print("Fix 2 — category split")
    print(f"  spend_category populated : {spend_count}")
    print(f"  fraud_label populated    : {fraud_count}")
    print(f"  neither (blank category) : {len(rows) - spend_count - fraud_count}\n")
    print(f"Added columns: {', '.join(NEW_COLUMNS)} (originals untouched)")


if __name__ == "__main__":
    sys.exit(main())
