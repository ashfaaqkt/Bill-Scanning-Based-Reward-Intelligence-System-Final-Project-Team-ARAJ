# Bill Scanning Based Reward & Intelligence System
### Final Year Project — BITS Pilani Digital · B.Sc. Computer Science · Group 120

> **Advisor:** Prof. Uma Sankara Rao
> **Team ARAJ:** Ashfaaq Feroz Muhammad · Arpan Chatterjee · Jyoti Kataria · Ranjeet Singh

---

## Project Overview

A production-grade AI + ML system where consumers scan retail receipts, extract structured data via OCR, detect fraud, learn user spending patterns, and receive personalised rewards.

**PoC Reference →** [Phase 3 PoC Repo](https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-study-project-bits-poc-phase-3-Team-ARAJ) (for read only)

### ML results (as of Aug 7, 2026)

| Model | Type | Result | Target |
|---|---|---|---|
| Category classifier | Supervised — TF-IDF + Random Forest | test macro-F1 **0.942** / acc 0.944 | 0.80 ✅ |
| Anomaly detector | **Unsupervised** — Isolation Forest | FPR **13.2%**, 100% recall ≥10× | <15% ✅ |
| Fraud tamper CNN | Supervised transfer learning — MobileNetV2 @ 448 | AUC **0.805** · **0.864** on real receipts | 0.90 ⚠️ |
| Recommender | Content-based ranking (not trained) | no offline metric possible | NDCG@5 ⏳ |
| Reward ranker | — | not started (NB 05) | — |

All five ML endpoints are wired and backed by real logic. Perceptual-hash duplicate
detection is a deterministic algorithm, not a learned model.

Per-model detail, comparisons and **limitations** → [`report/model_cards/`](report/model_cards/README.md).
Fraud evaluation in full → [`report/fraud_test_report.md`](report/fraud_test_report.md).

> The fraud CNN is below its 0.90 target and the reason is documented rather than
> glossed: 194 images from only 103 source receipts. Three evaluation faults found in
> Sprint 3 — unopenable PDFs, source-receipt leakage, and a JPEG compression shortcut
> worth AUC 0.690 on its own — were corrected, which *lowered* the reported number
> before better input resolution raised it again.

---

## Repository Structure
```
/
├── backend/          Node.js + Express + Firebase (delegates OCR to ml-service)
├── frontend/         Static HTML / CSS / JS UI
├── ml-service/       Python Flask ML microservice (Gemini OCR + ML models)
├── dataset/          Receipt dataset (CSVs tracked, images external)
├── docs/             Project documentation (setup, architecture, API, contributing)
├── notebooks/        Jupyter training experiments (01, 02, 03 executed with outputs)
└── report/           Report, model cards, figures and results CSVs
```

See docs/SETUP.md for full local setup instructions.

---

## 📚 Documentation

**Quick Links to All Documentation:**

| Document | Purpose | For Whom |
|---|---|---|
| **[SETUP.md](docs/SETUP.md)** | Local development environment setup, team member implementation guide | All team members, anyone setting up locally |
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System design, data flow, ML pipeline structure, tech stack | Architects, lead dev, anyone understanding the system |
| **[API.md](docs/API.md)** | Complete API reference for backend and ML service endpoints | Backend dev, frontend dev, integration testing |
| **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** | Contribution guidelines, Git workflow, code standards | All team members before making changes |
| **[dataset/DATA_PREP.md](dataset/DATA_PREP.md)** | Prepared training-data outputs, schemas, and caveats | Anyone training the ML models |
| **[report/model_cards/](report/model_cards/README.md)** | Per-model algorithm, data, comparison, results and limitations | Viva prep, report writing, anyone quoting a number |
| **[report/fraud_test_report.md](report/fraud_test_report.md)** | Full fraud evaluation — splits, ablation, significance testing | Fraud module review |

**Start Here:**
1. **New to the project?** → Read [SETUP.md](docs/SETUP.md) to get your environment running
2. **Need to understand the system?** → Read [ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. **Building an API call?** → Check [API.md](docs/API.md)
4. **Making a contribution?** → Follow [CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## Team & Branch Rules

| Member | Role | Branch |
|---|---|---|
| Ashfaaq Feroz | Lead Dev + Chief Editor | `main` (protected) |
| Arpan Chatterjee | ML Research + Dataset | `arpan/classifier` |
| Jyoti Kataria | Data + Docs | `jyoti/data-docs` |
| Ranjeet Singh | Fraud + Testing | `ranjeet/fraud-testing` |

**Rules:**
- `main` is protected — Ashfaaq merges only
- All work goes to `dev` first via Pull Request
- Never push directly to `main`
- Daily push by 9pm — even if small

---

## Academic Context

- Degree: B.Sc. Computer Science — BITS Pilani Digital
- Group: 120 · Advisor: Prof. Uma Sankara Rao
- License: MIT — Educational. Free to inspect and learn from with attribution.
