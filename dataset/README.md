# Dataset

## Sources

| Source | Count | Owner | Status |
|---|---|---|---|
| CORD (Clova OCR) | ~1000 | Arpan | Download from github.com/clovaai/cord |
| SROIE (ICDAR 2019) | ~973 | Arpan | Download from rrc.cvc.uab.es |
| Indian receipts (English) | 100 target | Jyoti | Photographed locally |
| Tampered (generated) | 100 target | Ranjeet | generate_tampered.py |

## processed/receipts_master.csv Schema

```
image_path, merchant, date, total, category, items_text, source
```

## processed/labels.csv Schema

```
image_path, label, labelled_by, notes
```

Labels: genuine / tampered / blurry / multi-bill / handwritten_edit

## Note

Raw images are NOT committed to Git (too large).
Only CSV files are tracked.
Store images in shared Google Drive —.<https://drive.google.com/drive/folders/10i_o-jpTaQv2Zk2jJVRCUc3muzCGLB8Z?usp=share_link>
