# Engineering & Evaluation Documentation

This folder holds the written evaluation record for the project: the per-model
cards, the fraud evaluation, the sprint summary, and the progress report
prepared for our supervisor.

## Structure

> **Scope of this folder.** What lives here is engineering documentation —
> written in Markdown, versioned alongside the code it describes, so a figure
> quoted in a card can always be traced to the CSV and the script that produced
> it. The academic submission documents are prepared and submitted separately
> and are not part of this repository.

| Path | Contents |
|---|---|
| `model_cards/` | One card per ML model — algorithm, data, comparison, results, limitations |
| `fraud_test_report.md` | Full fraud-detection evaluation (Sprint 3) |
| `sprint3_summary_report.md` | Sprint 3 summary — what changed and why |
| `assets/` | Figures (`fig_*.png`) and every results CSV behind them |
| `Team_ARAJ_Progress_Report_v5.pdf` | Progress report for Prof. Uma. Superseded revisions are not retained: v2 carried a transposed fraud-label split (genuine 64.5% / tampered 32.5%, when it is the reverse) that v3 corrected and stated openly; v4 added the collaborative filter, the reward evaluation and the integration defects found running the stack end to end; v5 records the final thresholds and the TC-26 result |

## Results at a glance (Aug 19, 2026)

| Model | Result | Target | Status |
|---|---|---|---|
| Category classifier | test macro-F1 **0.942** / acc 0.944 | 0.80 | ✅ Beaten |
| Anomaly detector | FPR **13.2%**, 100% recall ≥10× | <15% | ✅ Met |
| Fraud CNN | AUC **0.805** · **0.864** on real receipts | 0.90 | ⚠️ Not met |
| Recommender (SVD + content) | NDCG@5 **0.7984** *on synthetic interactions* | NDCG@5 0.70 | 🔸 Built & wired; target not claimed |

Every figure regenerates from the commands in `fraud_test_report.md` §7. Model
detail and limitations: [`model_cards/README.md`](model_cards/README.md).

> **Read `fraud_test_report.md` §6 alongside the fraud number.** The CNN and the
> perceptual-hash check were both dead in the running pipeline until 19 Aug —
> the upload path never passed the image, and no hash was ever stored. The
> evaluation here was measured directly against the corpus and is unaffected, but
> the running system did not produce these scores until those seams were fixed.

## A note on what is *not* served

`ml-service/forensics.py` is present but never called at runtime, and that is
deliberate rather than unfinished. It is a 31-feature hand-designed tamper
baseline built to test whether the CNN's ceiling was a property of the method or
of the corpus. It reaches AUC 0.736 alone, and rank-average fusion with the CNN
*lowers* the served result from 0.805 to 0.790. We keep the code because the
negative result is part of the evidence; we do not serve it because serving it
would make the system worse. Full working: `fraud_test_report.md` §4.

Documentation owner: Jyoti (structure + writing) · Ashfaaq (evaluation figures)
