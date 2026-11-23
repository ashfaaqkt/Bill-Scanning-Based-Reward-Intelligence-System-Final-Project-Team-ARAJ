# Research — multilingual, multi-currency receipt intelligence

*Branch `Research-Programs` only. Nothing here is on `main` or `dev`.*

The faculty-facing summary is
[`report/research_brief/ARAJ_research_brief.pdf`](report/research_brief/ARAJ_research_brief.pdf)
(5 pages).

## Problem statement

The capstone system (`v1.0-fyp`) reads Indian receipts with a schema-constrained
vision-language model and turns them into rewards, fraud signals and
recommendations. Audited for Gulf use, it turned out to understand only rupees
written in Latin digits. It had no currency field, an amount parser that removed
every comma, and a date parser that knew neither Eastern Arabic digits nor
Arabic month names. The failure mode is silent: a SAR receipt whose currency
mark trails its digits was credited as rupees. The research question is what it
takes to make receipt extraction, verification and reward logic correct in a
multilingual, multi-currency market, and how to show that honestly with very
little real data.

## What is where

| Path | What |
|---|---|
| `dataset/gulf_synthetic/` | Generator + ground-truth CSV for 48 **synthetic** receipts (images git-ignored, rebuilt from seed 2026) |
| `dataset/gulf_real/` | Git-ignored home for real, consented, redacted Gulf receipts. **Empty: none collected yet** |
| `research/eval/run_eval.py` | Evaluation harness: oracle dry run, live Gemini with four prompt ablations, EasyOCR baseline |
| `research/eval/js_normalize.js` | Runs a code version's **own** backend parsers (v1.0's are cut verbatim out of its `server.js`) |
| `research/models/multicurrency.py` | Classifier, anomaly, reward and tamper experiments; `--mode inr_only\|multi` loads either model set |
| `research/config/fx_rates.json` | Static, dated FX table (`2026-11-19.1`) |
| `research/results/` | Every table and chart quoted anywhere (tracked) |
| `research/tests/` | Generator determinism, harness dry run, Arabic parsing through the real code |
| `report/model_cards/*.md` | Each card gains a "Currency limitations" section |

## Reproduce

```bash
make all          # venv → data → models → eval → baselines → test
make live         # opt-in and billed: needs GEMINI_API_KEY exported in the shell
```

`make eval` checks out `v1.0-fyp` and `ed232ab` (main just before the currency
fix) into temporary worktrees. The tag is only read, never moved.

## Limitations

- **`main` is INR-only by design.** It refuses every other currency with HTTP
  422. Multi-currency behaviour exists only on this branch, behind
  `SUPPORTED_CURRENCIES`.
- **All Gulf results are synthetic.** 48 rendered receipts, 12 per currency, with
  no camera noise, paper or real typography. They test parsing and gating. They
  say nothing about real-world accuracy.
- **The dry run assumes perfect transcription.** It isolates post-processing.
  OCR accuracy on Arabic receipts is **not measured**.
- **No live model runs** were made for the results here, so all four prompt
  ablations are **not measured**.
- **No layout-model baseline** (LayoutLMv3 / Donut) was run. Neither public
  checkpoint has Arabic training data, so it would need fine-tuning first.
- **The labelled corpus has no Gulf data.** The model experiments use the only
  non-INR labels that exist: CORD (IDR) and SROIE (MYR).
- **Static FX.** One dated table. IDR and MYR are excluded because no verified
  dated rate was obtained.
- **Small sample.** One receipt moves a per-currency rate by about 8 points, so
  no confidence intervals are claimed.

## Experiment log

All numbers are on the 48-receipt synthetic set unless stated. Full tables are
in `research/results/comparison.md` and `research/results/models/multicurrency.md`.

| Date | Experiment | Result (measured) |
|---|---|---|
| 2026-11-22 | Before/after, oracle extraction | Whole-receipt success: v1.0-fyp **18.8%** → main before fix **25.0%** (blur-gate fix only) → v1.1 **97.9%** |
| 2026-11-22 | Foreign receipts credited as INR | v1.0: **4 of 48** (8.3%). v1.1: **0** |
| 2026-11-22 | Remaining v1.1 failure | 1 clean Arabic receipt (gs_000) refused by the shipped blur gate. Too little ink for its 2–98 percentile contrast stretch, so it scores 0.0 |
| 2026-11-22 | EasyOCR (ar+en) + rules | Whole-receipt **25.0%**. Merchant 72.9%, date 58.3%, total 47.9%, currency 50.0%. Reads ₹ as "5" and reverses Arabic word order |
| 2026-11-22 | Gemini ablations (4 prompts) | **Not measured** (no key used) |
| 2026-11-22 | Classifier + currency feature (real IDR/MYR split) | Macro-F1 **0.950 → 0.831**. Rejected: currency proxies the source corpus |
| 2026-11-22 | Anomaly reference strategy (real held-out) | FPR IDR 17.2% vs 16.7%, MYR 9.9% vs 10.3% (single INR ref vs per-currency). Pooled per-currency figure = 13.2%, which matches the v1.0 card |
| 2026-11-22 | Reward points, INR formula vs FX | Synthetic SAR/AED/QAR earn about 29×/31×/32× fewer base points if their amounts are read as INR (computed, not measured) |
| 2026-11-22 | Tamper CNN on synthetic receipts | 0 of 48 flagged at 0.82, maximum 0.193. Smoke test on rendered images only |
| 2026-11-22 | `fetch_models.py` | All five v1.0-fyp release binaries match the local `ml-service/models` byte for byte (SHA-256) |
| 2026-11-22 | Live production check (owner, by hand) | Non-INR receipts refused as intended. Indian receipts with **no ₹/Rs printed are also refused** (`CURRENCY_NOT_DETECTED`), and that is accepted as intended. Rate not measured |

## Open questions

1. How much of the 97.9% survives **real** Arabic OCR? Run `make live` first on
   the synthetic set, then on real receipts once they exist.
2. Does the Arabic-hints prompt measurably help, or only lengthen the prompt?
3. Indian receipts that print no ₹ **are** refused in production (observed in
   the owner's live tests, accepted as intended). Still open: **how many** of
   the 100 real Indian receipts this affects, and whether a stricter GSTIN /
   +91 rule could rescue them without crediting foreign amounts as INR.
4. Should the blur gate's contrast stretch use a wider percentile band, or an
   ink-coverage floor, so sparse receipts are not scored as blank pages?
5. Does the tamper CNN transfer to Arabic script at all? That needs a tampered
   Gulf subset.
6. Hijri dates are refused today. Is conversion worth a dependency, or is
   refusal the right product behaviour?
