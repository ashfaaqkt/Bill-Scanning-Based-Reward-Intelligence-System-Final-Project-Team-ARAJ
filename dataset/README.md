# Dataset

## Sources & Status

| Source | Count | Owner | Images stored at | In `receipts_master.csv`? |
|---|---|---|---|---|
| CORD (Clova OCR) | 800 annotations | Arpan | `dataset/temp_cord/` (JSON tracked, images external) | ✅ 800 rows |
| SROIE (ICDAR 2019) | 973 annotations | Arpan | `dataset/temp_sroie/` (entity `.txt` tracked, images external) | ✅ 973 rows |
| Indian receipts (Jyoti) | 100 | Jyoti | `dataset/indian/` (gitignored, on Drive) | labelled in `labels.csv` |
| Tampered (generated) | 100 | Ranjeet | `dataset/tampered/` (gitignored, on Drive) | labelled in `labels.csv` |
| Test bills | 5 | Ashfaaq | `dataset/test_bills/` | ✅ in repo (OCR smoke testing) |

> **Note:** `receipts_master.csv` is now **populated (1,973 rows)** from the CORD + SROIE annotations — it does **not** require the images to be downloaded. The receipt **images** (genuine / tampered / Indian) are still only on Drive and are needed for the fraud CNN (Notebook 03).

| Member | Dataset | Drive Link |
|---|---|---|
| Jyoti | 100 Indian receipt photos | [Jyoti's Drive](https://drive.google.com/drive/folders/10i_o-jpTaQv2Zk2jJVRCUc3muzCGLB8Z) |
| Ranjeet | 100 generated tampered images | [Ranjeet's Drive](https://drive.google.com/drive/folders/1yWlgYeTG1kumoUOZEtLv_rRmwwxUnVjF?usp=share_link) |
| Arpan | CORD + SROIE (~1800 images) | ⚠️ Link not yet shared (annotations already in repo) |

## Folder Structure

```
dataset/
  temp_cord/          ← CORD JSON annotations (tracked); images/ external
  temp_sroie/         ← SROIE entity .txt annotations (tracked); images/ external
  indian/             ← Jyoti's Indian receipt photos (gitignored, on Drive)
  tampered/           ← Ranjeet's tampered images (gitignored, on Drive)
  genuine/            ← original source images (gitignored)
  test_bills/         ← 5 sample bills for OCR smoke testing (in repo)
  processed/
    labels.csv                    ← 200 ground-truth fraud labels (Ranjeet 100 + Jyoti 100)
    receipts_master.csv           ← 1,973 consolidated rows (CORD + SROIE + 200 labelled)
    processed_labels_arpan.csv    ← detector output — QUARANTINED (see below), do not use
    category_dataset.csv          ← cleaned spend-category data for NB 02 (generated)
    category_{train,val,test}.csv ← stratified 70/15/15 splits (generated)
    fraud_manifest.csv            ← fraud labels + image availability for NB 03 (generated)
    fraud_{train,val}.csv         ← stratified 80/20 genuine/tampered splits (generated)
    missing_images_report.csv     ← which referenced images exist locally (generated)
    synthetic_user_interactions.csv ← SYNTHETIC user×category data for NB 04 (generated)
  build_receipts_master.py   ← builds receipts_master.csv from CORD + SROIE + labels
  download_annotations.py    ← fetches CORD/SROIE annotation files
  prepare_dataset.py         ← cleans/splits data into the train-ready files above (no training)
  generate_tampered.py       ← creates tampered variants (brightness, duplicate_copy, number_overwrite, handwritten)
  exact_duplicate_check.py   ← flags exact duplicate receipts from CSV
  perceptual_hash.py         ← pHash image similarity comparison tool
  fraud_detector.py          ← standalone multi-signal fraud scorer
  process_labels_arpan.py    ← runs Arpan's detector over labels.csv (needs real images — see below)
```

## Schemas

`processed/receipts_master.csv`
```
image_path, merchant, date, total, category, items_text, source
```

`processed/labels.csv`
```
image_path, label, labelled_by, notes
```
Labels: `genuine` / `tampered` / `multi_bill` / `handwritten`
(current counts: 129 tampered · 65 genuine · 5 multi_bill · 1 handwritten)

## Prepared training data

Run `python dataset/prepare_dataset.py` to regenerate the cleaned, split, train-ready
files (the `category_*`, `fraud_*`, `synthetic_*` outputs above). **This does no model
training** — it only cleans, splits and documents. Full details, schemas and caveats
(source leakage, heuristic 3-class labels, missing images, synthetic data) are in
[`DATA_PREP.md`](DATA_PREP.md).

## ⚠️ processed_labels_arpan.csv is quarantined

`process_labels_arpan.py` was run before the real receipt images were available, so it
**generated mock images** and **monkey-patched OCR**, then ran the detector on those fakes.
Every row therefore reads `LIKELY AUTHENTIC` (including all 129 tampered). The output is
invalid and is **excluded** from all prepared datasets. It becomes valid only after the real
images are downloaded and the monkey-patches removed. Use `labels.csv` as the fraud ground truth.

## Note

Raw images are NOT committed to Git (too large — gitignored). Only CSV/JSON annotation files
are version-controlled. The receipt **images** must be downloaded from each member's Drive
folder before running Notebook 03 (the fraud CNN). Notebooks 01, 02, 04, 05 run on the CSVs alone.
