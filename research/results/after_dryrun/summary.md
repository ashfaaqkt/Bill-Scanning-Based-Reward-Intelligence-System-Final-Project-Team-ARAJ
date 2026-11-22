# Evaluation: after_dryrun

- extractor: `oracle`, prompt: `as_is`, normaliser: `v1.1+`, supported currencies: `INR`
- dataset: `dataset/gulf_synthetic/gulf_synthetic.csv` — **SYNTHETIC**
- latency is wall time for extraction + normalisation on this machine — the model call is stubbed, so it EXCLUDES model time

n = 48

| metric | overall |
|---|---|
| merchant_exact | 0.979 |
| merchant_fuzzy | 0.979 |
| date_exact | 0.979 |
| total_exact | 0.979 |
| total_1pct | 0.979 |
| currency_exact | 0.979 |
| gate_correct | 1.000 |
| receipt_success | 0.979 |
| wrongly_accepted | 0.000 |
| wrongly_rejected | 0.000 |
| latency_ms median | 24.2 |

## By currency

| currency | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| AED | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| INR | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| QAR | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| SAR | 12 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 1.00 | 0.92 |

## By language

| language | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| ar | 12 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 1.00 | 0.92 |
| en | 24 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| mixed | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## By degradation

| degradation | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| blur | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| clean | 12 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 1.00 | 0.92 |
| low_light | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| rotation | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## By digits

| digits | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| eastern | 12 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 | 1.00 | 0.92 |
| latin | 36 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
