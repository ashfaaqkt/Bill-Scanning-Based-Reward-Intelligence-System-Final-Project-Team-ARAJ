#!/usr/bin/env python3
"""
Flatten Drive-downloaded receipt images to the flat layout the labels expect.

When you download the image folders from Drive, they arrive nested, e.g.:
    dataset/tampered/Tampered Images/Receipt 1_tampered.jpg
    dataset/indian/ Receipt Photos/Grocery Bills/Receipt 87 .jpg
...but labels.csv / fraud_manifest.csv reference flat paths:
    dataset/tampered/Receipt 1_tampered.jpg
    dataset/indian/Receipt 87.jpg

This script copies each labelled image up to its flat location, normalising the
messy names (extra spaces, "51 pdf" etc.) by matching on receipt number +
extension + the _tampered/_v2 suffixes. Originals in the nested subfolders are
kept (copy, not move) so it is safe and re-runnable.

It also writes dataset/processed/indian_category_folders.csv — the real spend
category for each Indian receipt, recovered from Jyoti's Drive folder names.

Run AFTER downloading the images from Drive, BEFORE rasterize_pdfs.py:
    python dataset/flatten_images.py
    python dataset/rasterize_pdfs.py     # then convert the PDF receipts to JPG
"""

import csv
import os
import re
import glob
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # dataset/
REPO = ROOT.parent                              # repo root
LABELS = ROOT / "processed" / "labels.csv"
CAT_OUT = ROOT / "processed" / "indian_category_folders.csv"
IMG_EXT = (".jpg", ".jpeg", ".png", ".pdf", ".heic")


def receipt_num(name: str):
    m = re.search(r"(\d+)", name)
    return m.group(1) if m else None


def main():
    if not LABELS.exists():
        print(f"Error: {LABELS} not found.")
        return

    rows = list(csv.DictReader(open(LABELS, newline="", encoding="utf-8")))

    # Source pool = images sitting in NESTED subfolders only (the Drive layout).
    # We exclude files already flattened directly into dataset/{tampered,indian}/ —
    # otherwise a re-run matches the flat copy (parent 'indian'/'tampered') and loses
    # the real category folder, corrupting indian_category_folders.csv. Sorted
    # deepest-first so the nested original always wins.
    def nested_images(sub):
        base = ROOT / sub
        files = [p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                 if os.path.isfile(p) and p.lower().endswith(IMG_EXT)
                 and Path(p).parent != base]           # skip already-flat copies
        return sorted(files, key=lambda p: -len(Path(p).parts))

    tampered_src = nested_images("tampered")
    indian_src = nested_images("indian")

    copied = skipped = unresolved = 0
    missing = []
    cat_map = []

    for r in rows:
        exp = r["image_path"]                       # e.g. dataset/indian/Receipt 51.pdf
        folder = os.path.dirname(exp)               # dataset/indian | dataset/tampered
        exp_base = os.path.basename(exp)
        exp_num = receipt_num(exp_base)
        exp_ext = os.path.splitext(exp_base)[1].lower()
        pool = tampered_src if "tampered" in folder else indian_src

        # 1) exact basename match anywhere in the pool
        match = next((p for p in pool if os.path.basename(p) == exp_base), None)
        # 2) fuzzy: same number + extension + same _tampered/_v2 flags
        if not match:
            v2 = "_v2" in exp_base
            tam = "_tampered" in exp_base
            cands = [p for p in pool
                     if receipt_num(os.path.basename(p)) == exp_num
                     and os.path.splitext(p)[1].lower() == exp_ext
                     and ("_v2" in os.path.basename(p)) == v2
                     and ("_tampered" in os.path.basename(p)) == tam]
            match = cands[0] if cands else None

        if not match:
            unresolved += 1
            missing.append(exp_base)
            continue

        dst = os.path.join(folder, exp_base)         # flat destination
        if os.path.abspath(match) == os.path.abspath(dst):
            skipped += 1                             # already flat
        else:
            shutil.copy2(match, dst)
            copied += 1

        # Capture the real category folder for Indian receipts (bonus ground truth)
        if "indian" in folder:
            parts = Path(match).parts
            cat = parts[-2] if len(parts) >= 2 else ""
            cat_map.append({"image_path": dst, "label": r["label"],
                            "drive_category_folder": cat})

    print(f"flattened(copied)={copied}  already-flat={skipped}  unresolved={unresolved}/{len(rows)}")
    if missing:
        print("  unresolved (download these from Drive):", missing[:12],
              "..." if len(missing) > 12 else "")

    if cat_map:
        with open(CAT_OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["image_path", "label", "drive_category_folder"])
            w.writeheader()
            w.writerows(cat_map)
        print(f"wrote {CAT_OUT.relative_to(REPO)} ({len(cat_map)} rows)")

    # Sanity: how many labels.csv paths now resolve as real files?
    present = sum(1 for r in rows if (REPO / r["image_path"]).exists())
    print(f"labels.csv images resolvable now: {present}/{len(rows)}")
    if present < len(rows):
        print("  (remaining PDFs will resolve as-is; run rasterize_pdfs.py to make them CNN-ready)")


if __name__ == "__main__":
    main()
