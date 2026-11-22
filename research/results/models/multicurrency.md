# Multi-currency model experiments

FX table: `research/config/fx_rates.json` version `2026-11-19.1` (static, as of 2026-11-19).

## A. Category classifier — text only vs text + currency

Same split as v1.0 (`category_train/test.csv`). Test-set currencies: {'IDR': 69, 'MYR': 147}. **No INR and no Gulf rows exist in this split.** Currency is a one-to-one proxy for the source corpus (CORD → IDR, SROIE → MYR).

| model | test_n | accuracy | macro_f1 | macro_f1_IDR | macro_f1_MYR |
|---|---|---|---|---|---|
| text_only (v1.0 features) | 216 | 0.954 | 0.950 | 0.603 | 0.980 |
| text + currency one-hot | 216 | 0.898 | 0.831 | 0.574 | 0.862 |

Predictions that differ between the two models: 13 of 216.

## B. Anomaly detector — reference strategy

Real held-out receipts (receipts_master, 25% split, seed 42). Training rows per currency: {'IDR': 592, 'MYR': 729}. Per-currency medians: {'IDR': 47249.5, 'MYR': 26.1}. Recall is against INJECTED SYNTHETIC outliers (v1.0's method).

| strategy | currency | test_n | fpr | recall@3x | recall@10x | recall@50x |
|---|---|---|---|---|---|---|
| inr_only_reference | IDR | 198 | 0.172 | 0.000 | 1.000 | 1.000 |
| inr_only_reference | MYR | 243 | 0.099 | 0.000 | 1.000 | 1.000 |
| per_currency_median | IDR | 198 | 0.167 | 0.000 | 1.000 | 1.000 |
| per_currency_median | MYR | 243 | 0.103 | 0.000 | 1.000 | 1.000 |


## C. Reward points — v1.0 formula vs FX-normalised (computed, not measured)

Base points on the 48 synthetic receipts. `inr_only` takes the amount as rupees, which is what v1.0 would do. `fx` converts with the static table first.

| currency | n | inr_only | fx | ratio |
|---|---|---|---|---|
| AED | 12 | 29 | 908 | 31.31 |
| INR | 12 | 216 | 216 | 1.00 |
| QAR | 12 | 20 | 633 | 31.65 |
| SAR | 12 | 31 | 896 | 28.90 |

## D. Tamper CNN on synthetic receipts — smoke test only

The served 448px model at threshold 0.82. Every synthetic receipt is untampered by construction, so a flag here is a false positive **on rendered images**, which differ from camera photos. This is not a measurement of real-world behaviour.

| currency | n | flagged_at_threshold | median_probability | max_probability |
|---|---|---|---|---|
| AED | 12 | 0.000 | 0.056 | 0.133 |
| INR | 12 | 0.000 | 0.065 | 0.193 |
| QAR | 12 | 0.000 | 0.068 | 0.118 |
| SAR | 12 | 0.000 | 0.061 | 0.138 |

## E. Recommender

The recommender ranks offers by spend **category** and a decayed category-interest vector. Amounts and currency never enter it, so there was nothing to make currency-aware. Its offer **catalogue** is priced in ₹, which is a product limitation, not a model one.
