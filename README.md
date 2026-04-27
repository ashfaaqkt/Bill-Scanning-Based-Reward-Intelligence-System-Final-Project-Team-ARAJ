# Bill Scanning Based Reward & Intelligence System
### Final Year Project — BITS Pilani Digital · B.Sc. Computer Science · Group 120

> **Advisor:** Prof. Uma Sankara Rao
> **Team ARAJ:** Ashfaaq Feroz Muhammad · Arpan Chatterjee · Jyoti Kataria · Ranjeet Singh

---

## Project Overview

A production-grade AI + ML system where consumers scan retail receipts, extract structured data via OCR, detect fraud, learn user spending patterns, and receive personalised rewards — powered by a multi-agent intelligence layer built with CrewAI.

**PoC Reference →** [Phase 3 PoC Repo](https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-study-project-bits-poc-phase-3-Team-ARAJ) (read only — do not modify)

---

## Repository Structure
```
/
├── backend/          Node.js + Express + Firebase + Gemini API
├── frontend/         Static HTML / CSS / JS UI
├── ml-service/       Python Flask ML microservice
├── dataset/          Receipt dataset (CSVs tracked, images external)
├── notebooks/        Jupyter training experiments
├── report/           Final year project report
└── docs/             Setup, API docs, architecture, contribution guide
```

See docs/SETUP.md for full local setup instructions.

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
