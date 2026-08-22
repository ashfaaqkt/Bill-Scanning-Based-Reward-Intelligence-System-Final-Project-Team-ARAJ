---
title: ARAJ ML Service
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Receipt OCR, tamper detection, categorisation and rewards
---

# ARAJ ML Service

The machine-learning service behind **Bill Scanning Based Reward & Intelligence
System** — a BITS Pilani Digital capstone project by Team ARAJ.

It is an internal HTTP API, not a user-facing app. The web client lives at
[araj-capstone.vercel.app](https://araj-capstone.vercel.app).

## Endpoints

| Route | Does |
|---|---|
| `GET /health` | liveness, and whether the model binaries loaded |
| `POST /ml/ocr` | blur gate → Gemini extraction with model fallback → multi-bill and handwriting checks |
| `POST /ml/classify` | spend category, TF-IDF + Random Forest |
| `POST /ml/fraud-score` | OCR rule signals + perceptual-hash duplicate check + MobileNetV2 tamper CNN at 448px |
| `POST /ml/anomaly` | spending anomaly, Isolation Forest |
| `POST /ml/update-profile` | decayed per-user interest vector |
| `POST /ml/recommend` | ranked offers, content + collaborative blend |

## Models

Weights are pulled at build time from the `v1.0-fyp` release of the project
repository — they are gitignored by design, so the image builds them in rather
than carrying them in source control.

| Model | Result |
|---|---|
| Category classifier | test macro-F1 **0.942** |
| Tamper CNN | AUC **0.805** pooled, **0.864** on real photographed receipts |
| Anomaly detector | FPR **13.2%** |

The tamper CNN is **below its 0.90 target** and documented as such. Two
unrelated methods plateau at the same level, which is evidence about the size of
the corpus rather than the architecture.

## Configuration

`GEMINI_API_KEY_1` is required; `_2` and `_3` are optional and only widen the
free-tier rate ceiling. Set them as Space secrets — never in the image.
