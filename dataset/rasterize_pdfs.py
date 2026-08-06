#!/usr/bin/env python3
"""
Rasterize PDF receipts to JPEG so the CNN can actually read them.

23 of the 200 labelled receipts arrived as PDFs. PIL cannot open a PDF, and the
NB 03 dataset loader only checks that the path exists — so those rows survived
the filter and then failed at load time. 19 of the 23 are genuine, which is the
minority class, so roughly a third of the genuine training set was silently
unusable. This script converts them in place (PDF is kept alongside the JPEG)
and repoints the manifest and splits at the new files.

Run:  python3 dataset/rasterize_pdfs.py
Idempotent — already-converted receipts are skipped.
"""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIRS = [REPO_ROOT / "dataset" / "indian", REPO_ROOT / "dataset" / "tampered"]
CSV_FILES = [
    REPO_ROOT / "dataset" / "processed" / "fraud_manifest.csv",
    REPO_ROOT / "dataset" / "processed" / "fraud_train.csv",
    REPO_ROOT / "dataset" / "processed" / "fraud_val.csv",
]


def rasterize(pdf_path):
    """PDF → JPEG (first page) via macOS sips. Returns the JPEG path, or None."""
    jpg_path = pdf_path.with_suffix(".jpg")

    if jpg_path.exists():
        return jpg_path

    result = subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "95",
         str(pdf_path), "--out", str(jpg_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not jpg_path.exists():
        print(f"  FAILED  {pdf_path.name}: {result.stderr.strip()}")
        return None

    # Only trust it if PIL — the thing that failed before — can open it.
    try:
        from PIL import Image
        with Image.open(jpg_path) as img:
            img.convert("RGB")
    except Exception as exc:
        print(f"  UNREADABLE  {jpg_path.name}: {exc}")
        jpg_path.unlink(missing_ok=True)
        return None

    return jpg_path


def repoint_csv(csv_path: Path, converted: dict) -> int:
    """Swaps .pdf image_path values for their .jpg equivalent. Returns rows changed."""
    if not csv_path.exists():
        return 0

    with open(csv_path, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)

    changed = 0
    for row in rows:
        path = row.get("image_path", "")
        if path in converted:
            row["image_path"] = converted[path]
            if "needs_pdf_conversion" in row:
                row["needs_pdf_conversion"] = "0"
            if "image_present" in row:
                row["image_present"] = "1"
            changed += 1

    if changed:
        shutil.copy(csv_path, csv_path.with_suffix(".csv.bak"))
        with open(csv_path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return changed


def main():
    if sys.platform != "darwin":
        sys.exit("This script uses macOS `sips`. On Linux use: pdftoppm -jpeg -r 150")

    converted = {}
    for image_dir in IMAGE_DIRS:
        for pdf_path in sorted(image_dir.glob("*.pdf")):
            jpg_path = rasterize(pdf_path)
            if jpg_path:
                relative_pdf = str(pdf_path.relative_to(REPO_ROOT))
                converted[relative_pdf] = str(jpg_path.relative_to(REPO_ROOT))
                print(f"  ok  {pdf_path.name} → {jpg_path.name}")

    print(f"\nRasterized {len(converted)} PDF(s).")

    for csv_path in CSV_FILES:
        changed = repoint_csv(csv_path, converted)
        print(f"  {csv_path.name}: {changed} row(s) repointed")


if __name__ == "__main__":
    main()
