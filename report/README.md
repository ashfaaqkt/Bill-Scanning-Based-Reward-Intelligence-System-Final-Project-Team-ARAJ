# Final Year Project Report

This folder holds the written evaluation record for the project.

## Structure

> **Scope of this folder.** What lives here is engineering documentation,
> versioned alongside the code it describes, so a figure quoted in a card
> can always be traced to the CSV and the script that produced it. The
> academic submission documents are prepared and submitted separately and
> are not part of this repository.

| Path | Contents |
|---|---|
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

## Chapters (as built, against the BITS template)

1. Introduction — problem, objectives O1–O7, scope
2. Implementation — architecture, stack, modules, algorithms, team workflow
3. Testing & Results — test register, per-model results, the evaluation faults found
4. Execution Environment — local run, planned cloud deployment
5. Project Execution — Git record, weekly progress, supervisor log
6. Conclusion & Future Work

Plus cover, declaration, abstract, contents, lists of figures/tables/abbreviations,
20 IEEE references and Appendices A–D.

Owned by: Jyoti (structure + writing) · Ashfaaq (final edit + PDF export)
