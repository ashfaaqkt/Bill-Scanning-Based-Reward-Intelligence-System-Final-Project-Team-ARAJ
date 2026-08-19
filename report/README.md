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
| `Team_ARAJ_Progress_Report_v4.pdf` | Progress report for Prof. Uma — v3 was copied across by hand and the two drifted. Superseded revisions are removed on build: v2 carried a transposed fraud-label split (genuine 64.5% / tampered 32.5%, when it is the reverse) that v3 corrected and stated openly; v4 adds the collaborative filter, the reward evaluation, and the twelve integration defects found running the stack end to end |

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
> perceptual-hash check were both dead in the deployed pipeline until 19 Aug —
> the upload path never passed the image, and no hash was ever stored. The
> evaluation here was measured directly against the corpus and is unaffected, but
> the running system did not produce these scores until those seams were fixed.

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
