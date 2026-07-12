#!/usr/bin/env python3
"""
Dataset preparation — Team ARAJ
Turns the raw consolidated data into clean, train-ready files for the ML notebooks.
NO model training happens here — this only cleans, splits and documents the data.

Inputs (read-only, never modified):
  dataset/processed/receipts_master.csv   (CORD + SROIE + processed_labels_arpan)
  dataset/processed/labels.csv            (ground-truth fraud labels)

Outputs (all written fresh, originals preserved):
  dataset/processed/category_dataset.csv          NB 02 — cleaned spend-category data
  dataset/processed/category_{train,val,test}.csv NB 02 — stratified 70/15/15 splits
  dataset/processed/fraud_manifest.csv            NB 03 — fraud labels + image availability
  dataset/processed/fraud_{train,val}.csv         NB 03 — stratified 80/20 (genuine/tampered)
  dataset/processed/missing_images_report.csv     which referenced images exist locally
  dataset/processed/synthetic_user_interactions.csv NB 04 — SYNTHETIC user x category (clearly flagged)
  dataset/DATA_PREP.md                            documentation of every output + caveats

Run:  python dataset/prepare_dataset.py
"""

import csv
import os
import re
import random
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent          # dataset/
REPO = ROOT.parent                              # repo root
PROC = ROOT / "processed"
SEED = 42
random.seed(SEED)

# ── helpers ────────────────────────────────────────────────────────────────

def clean_text(s):
    return re.sub(r"\s+", " ", (s or "").strip()).strip()

def parse_total(raw):
    """'1,591,600' -> 1591600.0 ; 'RM 9.00' -> 9.0 ; '' -> ''."""
    if not raw:
        return ""
    s = re.sub(r"[^0-9.,]", "", str(raw))
    if not s:
        return ""
    s = s.replace(",", "")            # treat comma as thousands sep
    if s.count(".") > 1:              # keep last dot as decimal
        head, _, tail = s.rpartition(".")
        s = head.replace(".", "") + "." + tail
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return ""

def parse_date(raw):
    """Normalise to YYYY-MM-DD; return '' if unparseable."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""

# heuristic 3-class mapper (clearly imperfect — documented in DATA_PREP.md)
FNB_KW = ("restaurant", "cafe", "caf ", "kopitiam", "coffee", "kitchen", "resto",
          "bistro", "food", "nasi", "mee", "noodle", "steak", "pizza", "burger",
          "bakery", "bake", "beverage", "seafood", "grill", "dining", "eatery",
          "snack", "juice", "warung", "catering", "seafood", "chicken", "rice",
          "tea", "drink", "milk")
GROCERY_KW = ("supermarket", "super market", "hypermarket", "hypermart", "mart",
              "grocery", "grocer", "minimart", "mini market", "sundry",
              "provision", "fresh", " market")

def map_3class(text):
    t = " " + (text or "").lower() + " "
    if any(k in t for k in FNB_KW):
        return "Food & Beverage"
    if any(k in t for k in GROCERY_KW):
        return "Supermarket / Grocery"
    return "General Retail"

def stratified_split(rows, key, ratios, seed=SEED):
    """Return list of split-name per row, stratified on row[key]."""
    buckets = {}
    for i, r in enumerate(rows):
        buckets.setdefault(r[key], []).append(i)
    assignment = [None] * len(rows)
    names = list(ratios.keys())
    for _, idxs in buckets.items():
        rnd = random.Random(seed)
        rnd.shuffle(idxs)
        n = len(idxs)
        c1 = int(n * ratios[names[0]])
        c2 = c1 + int(n * ratios[names[1]]) if len(names) > 2 else n
        for j, idx in enumerate(idxs):
            if j < c1:
                assignment[idx] = names[0]
            elif j < c2:
                assignment[idx] = names[1]
            else:
                assignment[idx] = names[-1]
    return assignment

def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.relative_to(REPO)}  ({len(rows)} rows)")

# ── A. category dataset (NB 02) ────────────────────────────────────────────

def build_category_dataset():
    print("\n[A] Category dataset (NB 02)")
    src = list(csv.DictReader(open(PROC / "receipts_master.csv", newline="", encoding="utf-8")))
    out = []
    dropped_empty = 0
    for r in src:
        if r["source"] == "processed_labels_arpan":
            continue  # quarantined: fraud rows, not category data (see DATA_PREP.md)
        source = r["source"]
        merchant = clean_text(r["merchant"])
        if merchant.upper() == "UNKNOWN":
            merchant = ""
        # SROIE's "items_text" column actually holds the address — relabel it.
        if source == "SROIE":
            address = clean_text(r["items_text"])
            items_text = ""
        else:  # CORD: real menu items, no address
            address = ""
            items_text = clean_text(r["items_text"])
        text = clean_text(f"{merchant} {items_text}")  # feature = merchant + items, NO source
        if not text:
            dropped_empty += 1
            continue
        out.append({
            "image_path": r["image_path"],
            "source": source,                       # metadata only — exclude from features
            "merchant": merchant,
            "address": address,
            "date": parse_date(r["date"]),
            "total": parse_total(r["total"]),
            "items_text": items_text,
            "text": text,
            "category": r["category"],              # 2-class (restaurant/retail)
            "category_3class": map_3class(text),     # heuristic 3-class
        })
    fields = ["image_path", "source", "merchant", "address", "date", "total",
              "items_text", "text", "category", "category_3class"]
    write_csv(PROC / "category_dataset.csv", fields, out)
    print(f"  dropped {dropped_empty} rows with empty text feature")

    # stratified 70/15/15 on the 2-class category
    split = stratified_split(out, "category", {"train": 0.70, "val": 0.15, "test": 0.15})
    for name in ("train", "val", "test"):
        rows = [out[i] for i in range(len(out)) if split[i] == name]
        write_csv(PROC / f"category_{name}.csv", fields, rows)
    return out

# ── B. fraud manifest (NB 03) ──────────────────────────────────────────────

def build_fraud_manifest():
    print("\n[B] Fraud manifest (NB 03)")
    src = list(csv.DictReader(open(PROC / "labels.csv", newline="", encoding="utf-8")))
    out = []
    report = []
    for r in src:
        rel = r["image_path"]
        exists = (REPO / rel).exists()
        is_pdf = rel.lower().endswith(".pdf")
        label = r["label"].strip()
        out.append({
            "image_path": rel,
            "label": label,                                   # 4-class ground truth
            "is_tampered": 1 if label == "tampered" else 0,    # binary (genuine=0)
            "binary_eligible": 1 if label in ("genuine", "tampered") else 0,
            "labelled_by": r.get("labelled_by", ""),
            "needs_pdf_conversion": 1 if is_pdf else 0,
            "image_present": 1 if exists else 0,
        })
        report.append({"image_path": rel, "label": label, "image_present": 1 if exists else 0})
    fields = ["image_path", "label", "is_tampered", "binary_eligible",
              "labelled_by", "needs_pdf_conversion", "image_present"]
    write_csv(PROC / "fraud_manifest.csv", fields, out)

    present = sum(r["image_present"] for r in out)
    print(f"  images present locally: {present}/{len(out)}  (rest are on Drive — see report)")
    write_csv(PROC / "missing_images_report.csv",
              ["image_path", "label", "image_present"], report)

    # stratified 80/20 on the binary-eligible (genuine + tampered) rows only
    binary = [r for r in out if r["binary_eligible"] == 1]
    split = stratified_split(binary, "label", {"train": 0.80, "val": 0.20})
    for name in ("train", "val"):
        rows = [binary[i] for i in range(len(binary)) if split[i] == name]
        write_csv(PROC / f"fraud_{name}.csv", fields, rows)
    return out

# ── C. synthetic user interactions (NB 04) — SYNTHETIC, clearly flagged ────

def build_synthetic_interactions(category_rows, n_users=60):
    print("\n[C] Synthetic user interactions (NB 04)  [SYNTHETIC DATA]")
    cats = ["Supermarket / Grocery", "Food & Beverage", "General Retail"]
    pool_by_cat = {c: [] for c in cats}
    for r in category_rows:
        pool_by_cat[r["category_3class"]].append(r)
    rnd = random.Random(SEED)
    rows = []
    for u in range(1, n_users + 1):
        uid = f"synthetic_user_{u:03d}"
        # each user has a preferred category (drives a higher rating there)
        pref = rnd.choice(cats)
        for _ in range(rnd.randint(6, 20)):
            cat = pref if rnd.random() < 0.6 else rnd.choice(cats)
            pool = pool_by_cat[cat] or category_rows
            src = rnd.choice(pool)
            base = 4 if cat == pref else 3
            rating = max(1, min(5, base + rnd.randint(-1, 1)))
            amount = src["total"] or f"{rnd.randint(50, 2000)}.00"
            rows.append({
                "user_id": uid,
                "category": cat,
                "merchant": src["merchant"] or "UNKNOWN",
                "amount": amount,
                "rating": rating,
                "is_synthetic": 1,
            })
    write_csv(PROC / "synthetic_user_interactions.csv",
              ["user_id", "category", "merchant", "amount", "rating", "is_synthetic"], rows)
    print(f"  generated {n_users} synthetic users, {len(rows)} interactions")
    return rows

# ── D. documentation ───────────────────────────────────────────────────────

def write_doc(cat_rows, fraud_rows, inter_rows):
    import collections
    cat2 = collections.Counter(r["category"] for r in cat_rows)
    cat3 = collections.Counter(r["category_3class"] for r in cat_rows)
    flab = collections.Counter(r["label"] for r in fraud_rows)
    present = sum(r["image_present"] for r in fraud_rows)
    doc = f"""# Dataset Preparation — Outputs & Caveats

Generated by `dataset/prepare_dataset.py` (seed={SEED}). **No model training is done here.**
Originals (`receipts_master.csv`, `labels.csv`) are untouched.

## NB 02 — Category classifier data
- `category_dataset.csv` — {len(cat_rows)} rows (CORD + SROIE only; the 200 `processed_labels_arpan`
  rows are **excluded** — they are fraud labels, not categories).
- Splits: `category_train.csv` / `category_val.csv` / `category_test.csv` (stratified 70/15/15 on `category`).
- 2-class `category`: {dict(cat2)}
- heuristic `category_3class`: {dict(cat3)}

### Caveats
- **Leakage:** `category` is sourced 1:1 from the dataset (CORD=restaurant, SROIE=retail).
  Train on the `text` column ONLY (merchant + items). **Do NOT feed `source`** as a feature.
- SROIE's original `items_text` was actually the **address** — moved to the `address` column;
  SROIE has no per-item text, CORD has no merchant.
- `category_3class` is a keyword heuristic (imperfect) — provided as an alternative target, not ground truth.
  For the 100 Indian receipts, real spend-category labels were recovered from the Drive folder
  structure into `indian_category_folders.csv` (Restaurant/Grocery/Pharmacy/etc.) — candidate ground truth.
- `total` is numeric but currencies differ by source (CORD≈IDR, SROIE≈MYR). `date` normalised to YYYY-MM-DD where present.
- **Status (NB 02): TRAINED** — 3-model comparison (LogReg / Linear SVM / Random Forest) on the 3-class
  target; Random Forest won (test macro-F1 0.942 / acc 0.944). `classifier.pkl` + `tfidf.pkl` in `ml-service/models/`.

## NB 03 — Fraud detection data
- `fraud_manifest.csv` — {len(fraud_rows)} rows from `labels.csv`. Columns include `is_tampered`
  (binary, genuine=0) and `binary_eligible` (genuine/tampered only).
- Splits: `fraud_train.csv` / `fraud_val.csv` (stratified 80/20 over genuine+tampered).
- Label counts: {dict(flab)}
- **Images present locally: {present}/{len(fraud_rows)}** ✅ — all downloaded from Drive and flattened into
  `dataset/tampered/` (100) and `dataset/indian/` (100). The 23 PDF receipts were rasterised to JPG via
  `dataset/rasterize_pdfs.py`, so all 200 are pixel-ready for the CNN.
- `processed_labels_arpan.csv` is **quarantined** (not used): its detector verdicts were computed on
  mock/generated images with monkey-patched OCR, so every row reads "LIKELY AUTHENTIC" — invalid.

## NB 04 — Recommender data
- `synthetic_user_interactions.csv` — {len(inter_rows)} rows across {len({r['user_id'] for r in inter_rows})} users (`is_synthetic=1`).
- **Real user data now available:** `backend/export_firestore.js` exports live receipt history to
  `dataset/processed/firestore_receipts.csv` (gitignored — regenerate on demand). Currently sparse
  (~19 receipts / 3 users), so combine with the synthetic set until real usage grows.

## Related scripts
- `dataset/rasterize_pdfs.py` — PDF receipts → JPG for the fraud CNN.
- `backend/export_firestore.js` — export real user receipt history for NB 04 / anomaly.

## Not done here (by design)
- This script only cleans/splits/documents — no training happens in it.
- Remaining external work: collect more real user activity (Firestore) for a meaningful collaborative filter;
  train the fraud CNN (NB 03) on Colab GPU.
"""
    (ROOT / "DATA_PREP.md").write_text(doc, encoding="utf-8")
    print(f"\n  wrote {(ROOT / 'DATA_PREP.md').relative_to(REPO)}")

# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("Dataset preparation (no training) — Team ARAJ")
    cat_rows = build_category_dataset()
    fraud_rows = build_fraud_manifest()
    inter_rows = build_synthetic_interactions(cat_rows)
    write_doc(cat_rows, fraud_rows, inter_rows)
    print("\nDone. See dataset/DATA_PREP.md for the summary.")

if __name__ == "__main__":
    main()
