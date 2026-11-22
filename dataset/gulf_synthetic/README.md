# Gulf synthetic receipt set — SYNTHETIC, research only

**Every receipt here is synthetic.** They are rendered by `generate.py` from
templates, with invented merchants and prices. They exist to test parsing, the
currency gate and the evaluation harness. **Do not report them as real data, and
do not use them for an accuracy claim about real Gulf receipts.**

| | |
|---|---|
| Size | 48 receipts (`--n` to change) |
| Currencies | SAR 12 · AED 12 · QAR 12 · **INR 12 (controls)** |
| Language | Arabic RTL 12 · English 24 (12 of them the INR controls) · bilingual 12 |
| Digits | Eastern Arabic (٠–٩ with ٫ ٬) 12 · Latin 36 |
| Degradation | clean · rotation (±7°) · Gaussian blur (σ 1.2–2.2) · low light, 12 each |
| VAT | KSA 15%, UAE 5%, Qatar none (as legislated); INR controls carry GST 5% and a GSTIN |
| Fonts | Noto Naskh Arabic, Noto Kufi Arabic, Noto Sans, Noto Sans Mono (SIL OFL, in `research/fonts/`) |
| Seed | 2026 (fixed) |

## Files

- `generate.py`: the generator. `make data` (or
  `research/.venv/bin/python dataset/gulf_synthetic/generate.py`) rebuilds everything.
- `gulf_synthetic.csv`: ground truth, **tracked**. Its columns follow
  `dataset/processed/receipts_master.csv` (`image_path, merchant, date, total,
  category, items_text, source, total_parsed, currency, spend_category,
  fraud_label`), then add `language, layout, digits, degradation, font,
  printed_date, printed_total, merchant_ar, notes`. `source` is always
  `synthetic`. `fraud_label` is empty because nothing here is tampered.
- `images/`: **git-ignored**. The images are deterministic and rebuilt from the
  seed, as `dataset/DATA_PREP.md` does for every other image set.

## TODO

- [ ] **Add real, consented Gulf receipts (target 100+).**

## Real receipts — `dataset/gulf_real/`

That folder is **git-ignored**, like `dataset/indian/` and `dataset/tampered/`.
Real images live in external storage (Drive), and only a labels CSV with
relative paths may be committed, as `DATA_PREP.md` describes for the Indian set.

Before any real image leaves the contributor's phone, apply this **redaction
rule**: cover customer and cashier **names**, **card numbers** (including the last
four digits), **phone numbers** and **loyalty or membership IDs** with a solid
opaque box. Blurring is not enough. Merchant name, date, line items, VAT number
and totals stay visible, because they are what is being measured. Record
consent per receipt in the labels CSV (`consent=yes`, collector, date).
