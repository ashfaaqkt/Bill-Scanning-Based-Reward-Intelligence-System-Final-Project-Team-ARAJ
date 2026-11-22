# Evaluation: pre_v1.1_main_dryrun

- extractor: `oracle`, prompt: `as_is`, normaliser: `v1.0`, supported currencies: `INR`
- dataset: `dataset/gulf_synthetic/gulf_synthetic.csv` — **SYNTHETIC**
- latency is wall time for extraction + normalisation on this machine — the model call is stubbed, so it EXCLUDES model time

n = 48

| metric | overall |
|---|---|
| merchant_exact | 0.979 |
| merchant_fuzzy | 0.979 |
| date_exact | 0.667 |
| total_exact | 0.354 |
| total_1pct | 0.354 |
| currency_exact | 0.250 |
| gate_correct | 0.917 |
| receipt_success | 0.250 |
| wrongly_accepted | 0.083 |
| wrongly_rejected | 0.000 |
| latency_ms median | 22.6 |

## By currency

| currency | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| AED | 12 | 1.00 | 1.00 | 0.50 | 0.08 | 0.08 | 0.00 | 0.92 | 0.00 |
| INR | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| QAR | 12 | 1.00 | 1.00 | 0.67 | 0.17 | 0.17 | 0.00 | 0.83 | 0.00 |
| SAR | 12 | 0.92 | 0.92 | 0.50 | 0.17 | 0.17 | 0.00 | 0.92 | 0.00 |

## By language

| language | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| ar | 12 | 0.92 | 0.92 | 0.17 | 0.17 | 0.17 | 0.00 | 0.92 | 0.00 |
| en | 24 | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 0.50 | 1.00 | 0.50 |
| mixed | 12 | 1.00 | 1.00 | 0.50 | 0.25 | 0.25 | 0.00 | 0.75 | 0.00 |

## By degradation

| degradation | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| blur | 12 | 1.00 | 1.00 | 0.50 | 0.25 | 0.25 | 0.25 | 1.00 | 0.25 |
| clean | 12 | 0.92 | 0.92 | 0.50 | 0.25 | 0.25 | 0.25 | 1.00 | 0.25 |
| low_light | 12 | 1.00 | 1.00 | 0.83 | 0.58 | 0.58 | 0.25 | 0.67 | 0.25 |
| rotation | 12 | 1.00 | 1.00 | 0.83 | 0.33 | 0.33 | 0.25 | 1.00 | 0.25 |

## By digits

| digits | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| eastern | 12 | 0.92 | 0.92 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 |
| latin | 36 | 1.00 | 1.00 | 0.89 | 0.47 | 0.47 | 0.33 | 0.89 | 0.33 |
