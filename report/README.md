# Final Year Project Report

This folder contains the final IEEE-format project report.

## Structure

| Path | Contents |
|---|---|
| `ARAJ_Final_Report.pdf` | Final submitted report (add when complete) |
| `model_cards/` | One card per ML model — algorithm, data, comparison, results, limitations |
| `fraud_test_report.md` | Full fraud-detection evaluation (Sprint 3) |
| `sprint3_summary_report.md` | Sprint 3 summary — what changed and why |
| `assets/` | Figures (`fig_*.png`) and every results CSV behind them |

## Results at a glance (Aug 7, 2026)

| Model | Result | Target | Status |
|---|---|---|---|
| Category classifier | test macro-F1 **0.942** / acc 0.944 | 0.80 | ✅ Beaten |
| Anomaly detector | FPR **13.2%**, 100% recall ≥10× | <15% | ✅ Met |
| Fraud CNN | AUC **0.805** · **0.864** on real receipts | 0.90 | ⚠️ Not met |
| Recommender | content-based; no offline metric | NDCG@5 0.70 | ⏳ Needs NB 04 |
| Reward ranker | not started | NDCG@5 0.70 | ❌ NB 05 |

Every figure regenerates from the commands in `fraud_test_report.md` §7. Model
detail and limitations: [`model_cards/README.md`](model_cards/README.md).

## Sections (target)

1. Introduction
2. Literature Review
3. System Design & Architecture
4. Dataset & Methodology
5. ML Models & Results
6. Evaluation & Testing
7. Conclusion & Future Work

Owned by: Jyoti (structure + writing) · Ashfaaq (final edit + PDF export)
