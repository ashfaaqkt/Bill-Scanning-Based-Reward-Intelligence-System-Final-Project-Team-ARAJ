**Bill Scanning Based Reward & Intelligence System**
Team ARAJ · BITS Pilani Digital · Group 120 · Advisor: Prof. Uma Sankara Rao

Release `v1.0-fyp` — the first complete version of the system, with every model
trained, wired and serving.

## Models

Five ML components, trained, wired into the upload path and surfaced in the UI.

| Component | Method | Result |
|---|---|---|
| Category classifier | TF-IDF + Random Forest | test macro-F1 **0.942** / acc 0.944 |
| Fraud tamper CNN | MobileNetV2 @ 448px | AUC **0.805** pooled, **0.864** on the 94 real photographs |
| Anomaly detector | Isolation Forest | FPR **13.2%** |
| Recommender | content + SVD hybrid | CV RMSE 0.9157 |
| Reward evaluation | NB 05 harness | NDCG@5 0.7984 on synthetic data |

The tamper CNN is **below its 0.90 target**. It is data-limited and documented as
such rather than presented as met.

The anomaly FPR is **set by the contamination parameter, not discovered**, so
clearing the target is true by construction. The earned figure is recall against
injected outliers: 100% at 10×, 0% at 3× and 5×.

**Neither recommender target is claimed.** Both the factorisation and its
evaluation run on generated interactions whose relevance labels come from the
same rule that produced the training ratings, so the score measures the
generator rather than the model.

## Pipeline

Gemini OCR with multi-key rotation and adaptive model fallback → category
classifier (used above 0.65 confidence, otherwise the extraction model's reading
stands) → fraud scoring: OCR rule signals, perceptual-hash near-duplicate
detection and the tamper CNN above 0.82 → spending anomaly → decayed interest
vector → ranked reward offers.

Duplicate claims are refused outright and logged: the same receipt from a second
account, and a second photograph of a receipt already claimed.

## Attached model binaries

These are gitignored by design, so a fresh clone has none of them. They are
attached so the exact weights behind the figures above stay recoverable.

| File | Used by | Backs |
|---|---|---|
| `tamper_cnn_cv_normalized_448.pt` | `fraud.py` | AUC 0.805 / 0.864 |
| `classifier.pkl` + `tfidf.pkl` | `classifier.py` | macro-F1 0.942 |
| `spending_anomaly.joblib` | `anomaly.py` | FPR 13.2% |
| `collab_filter.pkl` | `recommend.py` | RMSE 0.9157 (not claimed) |

`ml-service/fetch_models.py` downloads these **by exact filename** — renaming an
asset breaks it. Retraining reproduces the method but not these weights, so the
figures above belong to these files specifically.

## Status

**TC-26 passed on 21 August 2026.** Six receipts driven through the browser
against live Firestore and the live extraction model — three genuine across
three spend categories, one tampered, one blurred, one containing two bills.
Every case behaved as specified, including both refusals.

Demonstration walkthrough: https://www.youtube.com/watch?v=k3eFlxkNR2g

**Deployed and publicly reachable since 22 August 2026** at
https://araj-capstone.vercel.app — the web client on Vercel, the API on Render,
and the ML service on Google Cloud Run with 2 GB in `asia-southeast1`. The model
binaries in this release are what the deployed service fetches at build time, so
the figures above describe the system that is actually running.

Three providers rather than one is a result, not a preference. The ML service
ran on Render until 22 August and could not stay: free services cap at 512 MB
and PyTorch alone is ~250 MB resident before the tamper checkpoint loads. That
failure was **silent** — the scoring calls degrade rather than raise, so
receipts were written as low risk carrying the 0.05 baseline. Verification
failure is now a refusal. The full account is in
[`ml-service/SPACE_README.md`](ml-service/SPACE_README.md), and the four
deployment defects are listed in the repository README.

## Note on the tag message

The annotation on this tag records the state **at tag time**, when TC-26 and
cloud hosting were both listed as open. Both have since been resolved as
described above. The annotation is left unedited as the historical record.
