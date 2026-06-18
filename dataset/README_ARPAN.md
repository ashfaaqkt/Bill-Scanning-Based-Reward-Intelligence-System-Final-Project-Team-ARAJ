# CORD & SROIE Datasets Integration & Master Receipts CSV Compilation
**Collaborator/Contributor: Arpan**

This directory contains the dataset preparation and master consolidation pipeline created by Arpan. The goal is to provide a rich dataset for receipt parsing and validation algorithms without bloating the repository with thousands of raw image files.

---

## What was Completed

### 1. Downloaded Annotations (Lightweight & Image-free)
Using Python range-requests, we extracted only the structured text annotations from CORD and SROIE parquet dataset archives on Hugging Face:
- **CORD annotations**: Saved **800 JSON** files under `dataset/temp_cord/json/` following the pattern `receipt_00000.json`.
- **SROIE annotations**: Saved **973 text** files under `dataset/temp_sroie/entities/` containing key information (`company`, `address`, `date`, `total`).
- **Zero images** were downloaded or added to keep the repository footprint small and fast.

### 2. Consolidated Master CSV (`receipts_master.csv`)
We compiled the master receipts catalog under `dataset/processed/receipts_master.csv` containing **1,973 records** in total:
* **800 CORD** parsed menu item listings.
* **973 SROIE** parsed transaction headers.
* **200 Arpan labels** copied from `dataset/processed/processed_labels_arpan.csv` (contains custom tampering annotations and fake receipt detector scores/flags).

---

## Codebase Additions

The following scripts were introduced to the repository to document and automate the pipeline:

### 1. [download_annotations.py](download_annotations.py)
* **Purpose**: Downloads only the text columns from the Hugging Face parquet cache files for CORD (`naver-clova-ix/cord-v1`) and SROIE (`rth/sroie-2019-v2`).
* **Usage**:
  ```bash
  python dataset/download_annotations.py
  ```

### 2. [build_receipts_master.py](build_receipts_master.py)
* **Purpose**: Parses the local JSON/text files from CORD and SROIE, maps them into standard master columns, reads the existing `processed_labels_arpan.csv` entries, and writes the consolidated records into `processed/receipts_master.csv`.
* **Columns in `receipts_master.csv`**:
  * `image_path`: Path reference matching the dataset directory.
  * `merchant`: Company or business name (from SROIE, `UNKNOWN` for CORD/Arpan labels).
  * `date`: Transaction date (from SROIE, empty for CORD/Arpan labels).
  * `total`: Normalized transaction total.
  * `category`: Categorized label (`restaurant` for CORD, `retail` for SROIE, custom labels for Arpan).
  * `items_text`: Line items parsed from CORD, address parsed from SROIE, verification flags for Arpan.
  * `source`: Dataset source identifier (`CORD`, `SROIE`, `processed_labels_arpan`).
* **Usage**:
  ```bash
  python dataset/build_receipts_master.py
  ```

---

## Verification & Summary

Total compiled master rows count: **1,973**
* CORD rows: 800
* SROIE rows: 973
* Arpan labels rows: 200

All files are staged, committed, and pushed to the remote branch `arpan/classifier` (tracking branch `arpan-classifier`). No changes were made to the `main` branch.
