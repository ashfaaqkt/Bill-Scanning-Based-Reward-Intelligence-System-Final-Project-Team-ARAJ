# Model Card — Spending Anomaly Detector

| | |
|:---|:---|
| **Trainer** | `ml-service/train_anomaly.py` |
| **Owners** | Ranjeet Singh (original scope) · Ashfaaq KT (Sprint 3 implementation) |
| **Task** | Flag transactions whose amount is unusual |
| **Learning type** | **Unsupervised** — there are no anomaly labels anywhere in the project |
| **Algorithm** | Isolation Forest (200 trees, contamination 0.12) |
| **Artifact** | `ml-service/models/spending_anomaly.joblib` (2.5 MB) |
| **Served by** | `ml-service/anomaly.py` → `/ml/anomaly` |
| **Status** | ✅ **In production, target met** |

---

## What it does — and what it does not

The route is specified as a **per-user** check: "is this amount unusual *for this
user*". That model cannot be trained — `firestore_receipts.csv` holds **19 real
transactions across 3 users** (15 / 3 / 1).

So the trained component is **population-level**, and `anomaly.py` layers the
per-user behaviour on top at serving time: once a user has **5+ receipts**, their
own median replaces the population reference. That needs no training and improves
as Firestore fills.

Amounts are compared as a **ratio to a reference**, never absolutely. This is what
lets a model trained on Indonesian and Malaysian receipts serve Indian ones.

The check is **one-sided**: only amounts *above* the reference can be flagged.
Inflating a receipt to earn more points is the fraud; an unusually small receipt
is not.

## Data

1,762 receipt amounts from `receipts_master.csv` — 790 IDR (CORD) + 972 MYR
(SROIE) — split 1,321 train / 441 test. Amounts became usable only after
`dataset/repair_master_schema.py` recovered them (58.9% → 100% parseable).

Feature: **one** — `log(amount) − log(reference)`. Reference medians are computed
on training data only.

## Performance

| Metric | Value |
|:---|---:|
| **False-positive rate** (held-out real, n=441) | **13.2%** — target < 15% ✅ |
| **Recall @ ≥10× typical** (injected synthetic) | **100%** |
| Recall @ 5× | 0% |
| Recall @ 3× | 0% |

**Read both numbers together, and read them sceptically:**

- The false-positive rate is **set by the `contamination` parameter, not
  discovered**. Clearing the 15% target is by construction. It is reported this
  way deliberately rather than presented as a result.
- Recall is measured against **injected synthetic outliers**, declared as
  synthetic. There are no labelled real anomalies to test against.
- Neither means anything alone: a model that flags nothing scores a perfect 0%
  FPR.

## Comparison — feature selection

| Feature set | FPR | Recall @10× |
|:---|---:|---:|
| amount + category + day + weekday | 16.6% | 39.0% |
| **amount only** | **13.2%** | **100%** |

Category and date columns act as noise. **This is a single-feature model, and a
single-feature Isolation Forest reduces to a percentile threshold** — stated
plainly rather than presented as something subtler.

## Limitations

1. **Cannot detect inflation below ~5×.** The cutoff sits between 5× and 10×.
2. **Effectively a threshold rule**, not a rich model (see above).
3. **Trained on IDR/MYR, served INR.** The ratio formulation makes this
   defensible, but the population fallback (**₹2,748**, the median of the 19 real
   Firestore receipts) rests on a very small sample. Update it as usage data
   accumulates.
4. **Per-user history is in-memory and per-process** — a serving convenience, not
   storage. It resets on restart; Firestore remains the source of truth.
5. **Only one algorithm was compared.** The sprint plan asks for Isolation Forest
   vs One-Class SVM vs LOF; only Isolation Forest was built.
6. **Ranjeet's `anomaly_detector.joblib` is not used.** It has
   `n_features_in_=1280` — the EfficientNet-B0 embedding width — making it an
   *image-novelty* detector, not a spending model. `anomaly.py` rejects any
   artefact whose feature count does not match.

## Reproduce

```bash
python3 dataset/repair_master_schema.py
ml-service/.venv/bin/python ml-service/train_anomaly.py   # serving env, for sklearn version match
```

Results: `report/assets/anomaly_results.csv`.
