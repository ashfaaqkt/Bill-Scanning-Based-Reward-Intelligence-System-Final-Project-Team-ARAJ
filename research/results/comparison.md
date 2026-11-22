# Comparison (synthetic set — not real-data accuracy)

| run | n | merchant_exact | merchant_fuzzy | date_exact | total_exact | total_1pct | currency_exact | gate_correct | receipt_success | wrongly_accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| before_v1.0_dryrun | 48 | 0.750 | 0.750 | 0.542 | 0.292 | 0.292 | 0.188 | 0.854 | 0.188 | 0.083 |
| pre_v1.1_main_dryrun | 48 | 0.979 | 0.979 | 0.667 | 0.354 | 0.354 | 0.250 | 0.917 | 0.250 | 0.083 |
| after_dryrun | 48 | 0.979 | 0.979 | 0.979 | 0.979 | 0.979 | 0.979 | 1.000 | 0.979 | 0.000 |
| baseline_easyocr | 48 | 0.667 | 0.729 | 0.583 | 0.479 | 0.500 | 0.500 | 0.812 | 0.250 | 0.000 |

Not run (no results): `gemini_schema_currency_live`

## receipt_success by currency

| run | AED | INR | QAR | SAR |
|---|---|---|---|---|
| before_v1.0_dryrun | 0.00 | 0.75 | 0.00 | 0.00 |
| pre_v1.1_main_dryrun | 0.00 | 1.00 | 0.00 | 0.00 |
| after_dryrun | 1.00 | 1.00 | 1.00 | 0.92 |
| baseline_easyocr | 0.33 | 0.17 | 0.25 | 0.25 |

## receipt_success by language

| run | ar | en | mixed |
|---|---|---|---|
| before_v1.0_dryrun | 0.00 | 0.38 | 0.00 |
| pre_v1.1_main_dryrun | 0.00 | 0.50 | 0.00 |
| after_dryrun | 0.92 | 1.00 | 1.00 |
| baseline_easyocr | 0.00 | 0.38 | 0.25 |

## receipt_success by digits

| run | eastern | latin |
|---|---|---|
| before_v1.0_dryrun | 0.00 | 0.25 |
| pre_v1.1_main_dryrun | 0.00 | 0.33 |
| after_dryrun | 0.92 | 1.00 |
| baseline_easyocr | 0.00 | 0.33 |

## receipt_success by degradation

| run | blur | clean | low_light | rotation |
|---|---|---|---|---|
| before_v1.0_dryrun | 0.00 | 0.25 | 0.25 | 0.25 |
| pre_v1.1_main_dryrun | 0.25 | 0.25 | 0.25 | 0.25 |
| after_dryrun | 1.00 | 0.92 | 1.00 | 1.00 |
| baseline_easyocr | 0.00 | 0.33 | 0.42 | 0.25 |
