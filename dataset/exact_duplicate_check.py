#!/usr/bin/env python3
"""
Flag exact receipt duplicates based on merchant + date + total.

Default input:
    dataset/processed/receipts_master.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find exact duplicate receipts using merchant/date/total keys."
    )
    parser.add_argument(
        "--csv",
        default="dataset/processed/receipts_master.csv",
        help="Path to receipts CSV file.",
    )
    parser.add_argument(
        "--merchant-field",
        default="merchant",
        help="CSV column name for merchant.",
    )
    parser.add_argument(
        "--date-field",
        default="date",
        help="CSV column name for date.",
    )
    parser.add_argument(
        "--total-field",
        default="total",
        help="CSV column name for total.",
    )
    parser.add_argument(
        "--image-path-field",
        default="image_path",
        help="CSV column name for image path (used in output only).",
    )
    parser.add_argument(
        "--normalize-merchant",
        action="store_true",
        help="Normalize merchant name before duplicate checks (case/punctuation insensitive).",
    )
    return parser.parse_args()


def normalize_merchant(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in str(name or ""))
    return " ".join(cleaned.split())


def normalize_total(value: str) -> str:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        number = Decimal("0")
    # Quantize to 2 decimals for reliable money comparison
    return str(number.quantize(Decimal("0.01")))


def duplicate_key(row: dict, merchant_field: str, date_field: str, total_field: str, normalize_merchant_name: bool) -> tuple[str, str, str]:
    raw_merchant = str(row.get(merchant_field, "")).strip()
    merchant = normalize_merchant(raw_merchant) if normalize_merchant_name else raw_merchant
    date = str(row.get(date_field, "")).strip()
    total = normalize_total(str(row.get(total_field, "")))
    return merchant, date, total


def run(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    groups: dict[tuple[str, str, str], list[tuple[int, dict]]] = defaultdict(list)
    row_count = 0

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line_num, row in enumerate(reader, start=2):  # header is line 1
            row_count += 1
            key = duplicate_key(
                row=row,
                merchant_field=args.merchant_field,
                date_field=args.date_field,
                total_field=args.total_field,
                normalize_merchant_name=args.normalize_merchant,
            )
            groups[key].append((line_num, row))

    duplicate_groups = [(key, entries) for key, entries in groups.items() if len(entries) > 1]
    duplicate_rows = sum(len(entries) for _, entries in duplicate_groups)

    print(f"scanned_rows: {row_count}")
    print(f"duplicate_groups: {len(duplicate_groups)}")
    print(f"duplicate_rows: {duplicate_rows}")

    if not duplicate_groups:
        print("No exact duplicates found for merchant+date+total.")
        return 0

    print("\nFlagged duplicates:")
    for idx, (key, entries) in enumerate(sorted(duplicate_groups, key=lambda x: x[0]), start=1):
        merchant, date, total = key
        print(f"\n[{idx}] merchant='{merchant}' date='{date}' total='{total}' count={len(entries)}")
        for line_num, row in entries:
            image_path = row.get(args.image_path_field, "")
            original_merchant = row.get(args.merchant_field, "")
            print(
                f"  line={line_num} image_path='{image_path}' "
                f"merchant_raw='{original_merchant}'"
            )

    return 1


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
