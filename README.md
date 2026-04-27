# Bill Scanning Based Reward & Intelligence System
### Final Year Project — BITS Pilani Digital · B.Sc. Computer Science · Group 120

> **Advisor:** Prof. Uma Sankara Rao
> **Team ARAJ:** Ashfaaq Feroz Muhammad · Arpan Chatterjee · Jyoti Kataria · Ranjeet Singh

---

## Project Overview

A production-grade AI + ML system where consumers scan retail receipts, extract structured data via OCR, detect fraud, learn user spending patterns, and receive personalised rewards.

**PoC Reference →** [Phase 3 PoC Repo](https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-study-project-bits-poc-phase-3-Team-ARAJ) (for read only)

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

## 📚 Documentation

**Quick Links to All Documentation:**

| Document | Purpose | For Whom |
|---|---|---|
| **[SETUP.md](docs/SETUP.md)** | Local development environment setup, team member implementation guide | All team members, anyone setting up locally |
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System design, data flow, ML pipeline structure, tech stack | Architects, lead dev, anyone understanding the system |
| **[API.md](docs/API.md)** | Complete API reference for backend and ML service endpoints | Backend dev, frontend dev, integration testing |
| **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** | Contribution guidelines, Git workflow, code standards | All team members before making changes |

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
