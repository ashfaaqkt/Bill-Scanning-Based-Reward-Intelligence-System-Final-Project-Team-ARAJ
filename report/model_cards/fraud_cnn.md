# Model Card — Receipt Tamper Detector (Fraud CNN)

| | |
|:---|:---|
| **Notebook** | `notebooks/03_fraud_detection.ipynb` |
| **Owners** | Ranjeet Singh (Sprint 2 model, dataset) · Ashfaaq KT (Sprint 3 evaluation, integration) |
| **Task** | Binary image classification — has this receipt been tampered with? |
| **Learning type** | **Supervised transfer learning** (ImageNet-pretrained, fine-tuned) |
| **Algorithm** | MobileNetV2 @ **448 × 448** |
| **Artifact** | `ml-service/models/tamper_cnn_cv_normalized_448.pt` (9.2 MB, full `nn.Module`) |
| **Served by** | `ml-service/fraud.py` → `check_tamper_cnn()` → `/ml/fraud-score` |
| **Status** | ⚠️ **In production as one signal — below the 0.90 target** |

---

## What it does

Predicts the probability that a receipt image has been digitally altered. It is
**one signal among several** in `fraud.py`, contributing +0.40 to the fraud score
above a **0.82** threshold, alongside perceptual-hash duplicate detection and
OCR-derived flags (blur, multi-bill, handwriting).

It is **not** an automatic rejection gate, and the system does not use it as one.
The only hard blocks in the pipeline are the cross-user fingerprint check and the
perceptual-hash near-duplicate check, both of which refuse a receipt already
claimed before any model verdict is applied.

> **Operating point moved 0.50 → 0.82 (20 Aug 2026).** 0.50 was the obvious
> midpoint, not a measured choice, and at AUC 0.805 it cost about 28% false
> positives on genuine receipts — roughly one honest bill in three carrying a
> tamper signal, which is frequent enough that the signal stops meaning
> anything. 0.82 is taken from the operating-point table below: 50.4% recall for
> 9.2% false positives. **Recall is halved, deliberately.** A signal nobody can
> act on is worth less than a narrower one that is usually right. Re-running the
> shipped model over the labelled corpus shows the same direction (29% → 3%
> false positives, 81% → 51% recall), though those images are its own training
> data and the out-of-fold figures above are the honest ones.

> **`handwritten_flag` no longer sets the tamper signal (20 Aug 2026).** It did,
> which conflated two independent findings: any handwritten receipt — the norm
> on small Indian bills — reported as though the CNN had fired, and the client
> printed the one finding twice, as "shows signs of editing" and as "handwriting
> detected". Handwriting keeps its own signal and its own +0.30. `tamper` now
> means only that the CNN cleared its threshold. Any measurement of tamper-signal
> frequency taken before this date is inflated by the handwriting cases.

> **Wiring note (19 Aug 2026).** This signal did not reach production until that
> date: the upload path called `/ml/fraud-score` without the image, and `torch`
> was absent from the serving venv, so every receipt scored the 0.05 fallback.
> Both are fixed and verified over HTTP — tampered images now mean 0.763 against
> 0.539 for genuine. The evaluation numbers below were always measured directly
> against the corpus and are unaffected.

## Data

194 labelled images from **103 unique source receipts** — 65 genuine, 129
tampered. The independent unit is the *receipt*, not the file: several tampered
variants derive from one original.

| Subset | n | Tampering | Origin |
|:---|---:|:---|:---|
| `dataset/tampered/` | 100 | synthetic, 4 modes from `generate_tampered.py` | derived |
| `dataset/indian/` | 94 | **real** | 65 genuine + 29 human-labelled tampered |

**Evaluation: 5-fold stratified grouped cross-validation**, grouped on source
receipt so no receipt appears in both train and test. Per fold: train 152–158
(78.4–81.4%), test 36–42 (18.6–21.6%). Every image is held out exactly once.

## Performance

| Metric | Value |
|:---|---:|
| **Pooled out-of-fold AUC** | **0.805** (95% CI [0.733, 0.872]) |
| **Real-receipt subset (n=94)** | **0.864** (95% CI [0.783, 0.934]) |
| Mean fold AUC | 0.811 ± 0.091 |
| Target | 0.90 — **not met** |

Quote the pooled figure. Mean-of-folds averages five small noisy scores; pooled
OOF scores all 194 predictions together and is the more stable statistic.

**Operating points** — there is no threshold that is both high-recall and
low-noise, which is the practical meaning of AUC 0.805:

| Threshold | Recall on tampered | False positives on genuine |
|---:|---:|---:|
| **0.82 — in use** | **50.4%** | **9.2%** |
| 0.74 | 57.4% | 20.0% |
| 0.60 | 65.1% | 27.7% |
| 0.20 | 89.9% | 47.7% |

Read down the right-hand column before quoting the left. There is no row here
that is both useful and quiet, and that — not the headline AUC — is the practical
limitation of this model. 0.82 was chosen because a signal that fires on a third
of honest receipts cannot be acted on, so its extra recall is not real recall.

## Comparison

| Approach | Pooled OOF AUC |
|:---|---:|
| JPEG quantization table only (pre-fix artifact) | 0.690 |
| Forensic features (31 hand-designed) | 0.736 |
| CNN @ 224 × 224 | 0.752 |
| Fusion (CNN 448 + forensics) | 0.790 |
| **CNN @ 448 × 448** | **0.805** ← selected |

**Why 448 over 224:** receipts are ~1200×1600, so a 224 input is a 7.1×
downscale that reduces an overwritten digit to ~6 pixels. Training at 448 raised
AUC 0.752 → 0.805, **statistically significant at p = 0.020** by paired bootstrap
clustered on source receipt (95% CI on the difference [+0.008, +0.100]).

**Why not fusion:** adding the forensic model *lowers* results (0.805 → 0.790).
The two correlate at Spearman ρ = 0.638 and the weaker model drags the stronger
one down. Reported as a negative result.

## Limitations

1. **Below target, and the constraint is data.** Best epoch was 4–14 of 15 in
   every fold — the model saturates then overfits. 65 genuine receipts sets the
   ceiling. A learning-curve probe over 24–103 receipts showed no upward trend,
   so more receipts *of the same kind* may not help; more *diverse* tampering
   probably would.
2. **77% of the tampered class is synthetic**, produced by our own script.
   Detecting it is a weaker claim than detecting real fraud. **The 0.864
   real-receipt figure is the honest estimate of real-world performance.**
3. **Three evaluation faults were found and corrected in Sprint 3** — 23
   unopenable PDFs, source-receipt leakage across splits, and a JPEG compression
   shortcut worth AUC 0.690 on its own. Any number predating those fixes is not
   comparable.
4. **Sprint 2's reported 0.76 could not be reproduced.** The delivered checkpoint
   loads as EfficientNet-B0, not the claimed MobileNetV2, and scores 0.555.
5. **Serving resolution must match training.** `fraud.py` resizes to 448 via a
   single `IMG_SIZE` constant — serving at 224 would silently degrade every
   prediction.
6. **`torch.load` needs `weights_only=False`** for this checkpoint (PyTorch ≥2.6
   changed the default). Without it, loading raises, the exception is swallowed,
   and every receipt gets the 0.05 baseline — a dead CNN that looks healthy.

## Reproduce

```bash
python3 dataset/rasterize_pdfs.py
python3 dataset/normalize_images.py
python  ml-service/train_fraud_cv.py --normalized --img-size 448
python  ml-service/make_report_figures.py
```

Full detail: `report/fraud_test_report.md`.
