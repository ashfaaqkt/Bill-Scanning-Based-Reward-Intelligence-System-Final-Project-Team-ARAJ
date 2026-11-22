# Evaluation: baseline_easyocr

- extractor: `easyocr`, prompt: `as_is`, normaliser: `v1.1+`, supported currencies: `INR`
- dataset: `dataset/gulf_synthetic/gulf_synthetic.csv` — **SYNTHETIC**
- latency is wall time for extraction + normalisation on this machine

n = 48

| metric | overall |
|---|---|
| merchant_exact | 0.667 |
| merchant_fuzzy | 0.729 |
| date_exact | 0.583 |
| total_exact | 0.479 |
| total_1pct | 0.500 |
| currency_exact | 0.500 |
| gate_correct | 0.812 |
| receipt_success | 0.250 |
| wrongly_accepted | 0.000 |
| wrongly_rejected | 0.188 |
| latency_ms median | 3689.8 |

## By currency

| currency | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| AED | 12 | 0.67 | 0.75 | 0.50 | 0.50 | 0.58 | 0.50 | 1.00 | 0.33 |
| INR | 12 | 0.75 | 0.83 | 0.75 | 0.58 | 0.58 | 0.25 | 0.25 | 0.17 |
| QAR | 12 | 0.67 | 0.75 | 0.58 | 0.42 | 0.42 | 0.58 | 1.00 | 0.25 |
| SAR | 12 | 0.58 | 0.58 | 0.50 | 0.42 | 0.42 | 0.67 | 1.00 | 0.25 |

## By language

| language | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| ar | 12 | 0.17 | 0.25 | 0.17 | 0.33 | 0.33 | 0.67 | 1.00 | 0.00 |
| en | 24 | 0.83 | 0.88 | 0.79 | 0.58 | 0.58 | 0.46 | 0.62 | 0.38 |
| mixed | 12 | 0.83 | 0.92 | 0.58 | 0.42 | 0.50 | 0.42 | 1.00 | 0.25 |

## By degradation

| degradation | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| blur | 12 | 0.42 | 0.58 | 0.08 | 0.08 | 0.08 | 0.08 | 0.75 | 0.00 |
| clean | 12 | 0.83 | 0.92 | 0.58 | 0.50 | 0.58 | 0.58 | 0.83 | 0.33 |
| low_light | 12 | 0.83 | 0.83 | 0.83 | 0.92 | 0.92 | 0.67 | 0.83 | 0.42 |
| rotation | 12 | 0.58 | 0.58 | 0.83 | 0.42 | 0.42 | 0.67 | 0.83 | 0.25 |

## By digits

| digits | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success |
|---|---|---|---|---|---|---|---|---|---|
| eastern | 12 | 0.42 | 0.58 | 0.08 | 0.08 | 0.17 | 0.33 | 1.00 | 0.00 |
| latin | 36 | 0.75 | 0.78 | 0.75 | 0.61 | 0.61 | 0.56 | 0.75 | 0.33 |
