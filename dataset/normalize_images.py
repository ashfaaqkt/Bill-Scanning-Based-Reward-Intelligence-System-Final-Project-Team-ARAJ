#!/usr/bin/env python3
"""
Remove the compression shortcut from the fraud dataset.

generate_tampered.py saves every tampered receipt at JPEG quality 95, so 104 of
129 tampered images carry PIL's quality-95 quantization table while most genuine
images keep their original camera table. A classifier can read that table and
score AUC 0.69 without looking at a single pixel — it detects "written by our
tampering script", not "tampered".

This script re-encodes EVERY labelled image through one identical path
(open -> RGB -> JPEG quality 95, no chroma subsampling) into dataset/normalized/,
so the quantization table is constant across both classes and carries no label
information by construction.

Originals are never modified. Writes dataset/processed/fraud_normalized.csv.

Run:  python3 dataset/normalize_images.py
Verify afterwards: the quantization-table probe should drop to ~0.50.
"""

import csv
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / "dataset" / "processed"
OUT_DIR = REPO_ROOT / "dataset" / "normalized"
OUT_CSV = PROCESSED / "fraud_normalized.csv"

QUALITY = 95
SUBSAMPLING = 0     # 4:4:4 — fixed, so chroma handling cannot differ either


def labelled_rows():
    """The 194 binary-task rows from the existing splits."""
    rows = []
    for name in ("fraud_train.csv", "fraud_val.csv"):
        with open(PROCESSED / name, newline="") as handle:
            for row in csv.DictReader(handle):
                if row["label"] in ("genuine", "tampered"):
                    rows.append(row)
    return rows


def main():
    rows = labelled_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filenames must stay unique, and the stem must survive unchanged so that
    # source-receipt grouping ('Receipt 10' vs 'Receipt 10_tampered') still works.
    stems = [Path(r["image_path"]).stem for r in rows]
    duplicates = {s for s in stems if stems.count(s) > 1}
    if duplicates:
        sys.exit(f"Stem collision would lose images: {sorted(duplicates)[:5]}")

    written = []
    for row in rows:
        source = REPO_ROOT / row["image_path"]
        target = OUT_DIR / f"{source.stem}.jpg"

        with Image.open(source) as handle:
            image = handle.convert("RGB")
            image.save(target, "JPEG", quality=QUALITY, subsampling=SUBSAMPLING)

        written.append({
            "image_path": str(target.relative_to(REPO_ROOT)),
            "label": row["label"],
            "original_path": row["image_path"],
            "source_folder": row["image_path"].split("/")[1],
        })

    with open(OUT_CSV, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["image_path", "label", "original_path", "source_folder"])
        writer.writeheader()
        writer.writerows(written)

    genuine = sum(1 for r in written if r["label"] == "genuine")
    print(f"Normalized {len(written)} images → dataset/normalized/ "
          f"({genuine} genuine / {len(written) - genuine} tampered)")
    print(f"  JPEG quality {QUALITY}, subsampling {SUBSAMPLING}, identical for both classes")
    print(f"Wrote {OUT_CSV.relative_to(REPO_ROOT)}")

    # Confirm the table really is constant now.
    tables = set()
    for record in written:
        with Image.open(REPO_ROOT / record["image_path"]) as handle:
            tables.add(tuple(handle.quantization[0][:16]))
    print(f"\nDistinct quantization tables across all images: {len(tables)} "
          f"({'PASS — no table can carry label information' if len(tables) == 1 else 'FAIL'})")


if __name__ == "__main__":
    sys.exit(main())
