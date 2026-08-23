# Bill Scanning Based Reward & Intelligence System
### Final Year Project — BITS Pilani Digital · B.Sc. Computer Science · Group 120

> **Advisor:** Prof. Uma Sankara Rao
> **Team ARAJ:** Ashfaaq Feroz Muhammad · Arpan Chatterjee · Jyoti Kataria · Ranjeet Singh

---

## Project Overview

A production-grade AI + ML system where consumers scan retail receipts, extract structured data via OCR, detect fraud, learn user spending patterns, and receive personalised rewards.

## ▶ Try the system

### **[araj-capstone.vercel.app](https://araj-capstone.vercel.app)**

Sign up, upload a receipt photo, and watch the pipeline run end to end —
extraction, categorisation, tamper and duplicate checks, anomaly scoring, points
and ranked rewards. That single link is all a reviewer needs.

> **What the web client is for.** This project was undertaken under the **AI/ML**
> genre, not full-stack web development. The interface exists to make the machine
> learning observable — it surfaces the category, the fraud verdict, the tamper
> score and the anomaly flag so the models can be watched working on a real
> receipt. The models, their evaluation and their limitations are the subject;
> the UI is the window onto them.

The two services behind it are documented for completeness. Neither is meant to
be visited directly — the ML service is an internal API, not a user-facing app.

| Tier | URL | Runs on |
|---|---|---|
| **Web client** — start here | **https://araj-capstone.vercel.app** | Vercel (static, never sleeps) |
| Backend API | `https://araj-backend.onrender.com` | Render, Singapore |
| ML service | `https://araj-ml-service-1012478382071.asia-southeast1.run.app` | Google Cloud Run, 2 GB, `asia-southeast1` |

**First upload after a quiet spell is slow.** The backend sleeps after 15 minutes
idle on Render's free tier and takes ~50s to wake; Cloud Run scales to zero and
cold-starts too. Open the site a minute before demonstrating, or use the
[recorded walkthrough](https://www.youtube.com/watch?v=k3eFlxkNR2g).

**PoC Reference →** [Phase 3 PoC Repo](https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-study-project-bits-poc-phase-3-Team-ARAJ) (read only) — the study project this capstone builds on.

### ML results (as of 23 Aug 2026)

| Model | Type | Result | Target |
|---|---|---|---|
| Category classifier | Supervised — TF-IDF + Random Forest | test macro-F1 **0.942** / acc 0.944 | 0.80 ✅ |
| Anomaly detector | **Unsupervised** — Isolation Forest | FPR **13.2%**, 100% recall ≥10× | <15% ✅ |
| Fraud tamper CNN | Supervised transfer learning — MobileNetV2 @ 448 | AUC **0.805** · **0.864** on real receipts | 0.90 ⚠️ |
| Recommender | Hybrid — content affinity + SVD collaborative filter (NB 04) | 5-fold CV RMSE **0.9157** | RMSE < 0.5 (notebook) / < 1.0 (plan) 🔸 **not claimed** |
| Reward ranker | Evaluation harness (NB 05), not a trained ranker | P@5 0.50 · R@5 0.8833 · NDCG@5 **0.7984** | NDCG@5 > 0.70 🔸 **cleared but not claimed** |

All five ML endpoints are wired and backed by real logic, and all five notebooks
carry outputs. Perceptual-hash duplicate detection is a deterministic algorithm,
not a learned model.

> **Both targets are stated above and neither is claimed. That is deliberate.**
> NDCG@5 0.7984 *clears* its 0.70 bar; RMSE 0.9157 misses the 0.5 the notebook
> header set and meets the 1.0 the sprint plan set — the two documents disagreed,
> which is itself worth knowing.
> Both the SVD and
> the evaluation run on `synthetic_user_interactions.csv`, where the relevance
> labels come from the same rule that generated the ratings — a strong score
> there measures the generator, not the ranker. NB 05 was also delivered as an
> evaluation harness rather than the XGBoost ranker the plan specified, so its
> "≥3 algorithms compared" criterion is unmet. See
> [`report/model_cards/recommender.md`](report/model_cards/recommender.md).

Per-model detail, comparisons and **limitations** → [`report/model_cards/`](report/model_cards/README.md).
Fraud evaluation in full → [`report/fraud_test_report.md`](report/fraud_test_report.md).

> The fraud CNN is below its 0.90 target and the reason is documented rather than
> glossed: 194 images from only 103 source receipts. Three evaluation faults found in
> Sprint 3 — unopenable PDFs, source-receipt leakage, and a JPEG compression shortcut
> worth AUC 0.690 on its own — were corrected, which *lowered* the reported number
> before better input resolution raised it again.

---

## Project status — 23 Aug 2026

**Released as [`v1.0-fyp`](https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-Final-Project-Team-ARAJ/releases/tag/v1.0-fyp).**
The release carries the four model binaries, which are gitignored by design — a
fresh clone has none of them, and `ml-service/fetch_models.py` pulls them by
exact filename.

**TC-26 passed on 21 Aug 2026.** Six receipts driven through the browser in one
session against live Firestore and the live extraction model: three genuine
across three spend categories, one tampered, one blurred, one containing two
bills. Every case behaved as specified, including both refusals.
[Recorded walkthrough](https://www.youtube.com/watch?v=k3eFlxkNR2g).

**Deployed and live since 22 Aug 2026** at
[araj-capstone.vercel.app](https://araj-capstone.vercel.app) — three tiers across
three providers, against live Firestore and the live extraction model. Getting
there took three attempts, and the failures are worth more than the outcome.

### How the hosting ended up on three providers

**1. Render, for everything.** The obvious first choice: one blueprint file
(`render.yaml`), one provider, no container work. The backend is Node, fits
comfortably, and **still runs there**.

**2. The ML service could not stay on Render.** Free web services are capped at
**512 MB**, and torch alone is ~250 MB resident before the tamper checkpoint
loads — OpenCV, pandas and scikit-learn sit on top of that. Render recorded
*"Instance failed"* at 20:11 on 22 Aug, the same minute the backend logged the
fraud, profile and recommend calls as unreachable.

> **The failure was silent, and that is the point.** All three calls degrade
> rather than error, so the upload still succeeded — and the receipt was stored
> as **Low risk with the 0.05 baseline, no signals and no perceptual hash**. A
> receipt that had never been checked was indistinguishable from one that
> passed. The upload path now refuses when verification is unavailable, and
> records why.

Render's private network is also unavailable between free web services, so the
internal address failed with `getaddrinfo ENOTFOUND araj-ml-service` and had to
become a public URL.

**3. Hugging Face Spaces was tried next**, and the service was containerised for
it. It was dropped once the tier that actually met the service's requirements
turned out to be a paid one.

**4. Google Cloud Run took it.** 2 GB, `asia-southeast1`, min 0 / max 2
instances, concurrency 8 — inside the free tier, and the tamper CNN returns real
probabilities there. The build is defined in `cloudbuild.yaml` at the repository
root rather than in the console, because a console Dockerfile trigger builds and
pushes but never deploys, which produced a green build sitting behind a
placeholder image.

**Why not Cloud Run from the start?** Three reasons, honestly ordered. Render
was the cheaper bet — the entire stack was expressible in one blueprint with no
Dockerfile. The constraint was invisible until runtime: the service came up,
passed its health check, and only died when `/ml/fraud-score` first imported
torch under a real upload, so nothing at planning time said "this needs 2 GB".
And Cloud Run's setup cost — Dockerfile, Artifact Registry, a Cloud Build
pipeline, a billing-enabled project — only paid for itself once a container
existed, which is exactly what the Hugging Face attempt produced.

### Live thresholds

| Constant | Value | Meaning |
|---|---|---|
| `BLUR_THRESHOLD` | 40 | Contrast-normalised sharpness over the ink only — **not** whole-frame Laplacian variance |
| `TAMPER_THRESHOLD` | 0.82 | The CNN contributes above this. 50.4% recall for 9.2% false positives |
| `PHASH_DISTANCE_THRESHOLD` | 6 | And the receipt totals must agree — an image match alone cannot refuse a user |
| `CLASSIFIER_MIN_CONFIDENCE` | 0.65 | Below this, the extraction model's category stands |

Each was set by measurement, not by assumption; the reasoning is in the model
cards and beside each constant in the code.

### What whole-stack testing found

**Twenty-seven integration defects** across six sessions, 17–22 Aug. None was
found by a component test, and the component tests passed throughout. Two meant
a model this repository described as live had never executed on a real upload —
the tamper CNN was called without the image, and the perceptual-hash check was
never given hashes to compare against. **A component test cannot see a seam.**

The last four came out of **deployment itself** (22 Aug), and three of those were
silent — they degraded the system without raising an error anywhere:

| # | Defect | Why it was invisible |
|---|---|---|
| 24 | `ML_SERVICE_URL` supplied scheme-less as `host:port` | Parsed as a relative path; every ML call failed as a connection error, not a config error |
| 25 | Render's internal hostname unresolvable between free services | `getaddrinfo ENOTFOUND araj-ml-service` — the private network does not exist on the free tier |
| 26 | 3-second HTTP timeouts tuned against localhost | Fine at ~5 ms on one machine, far too tight across regions and a cold start |
| 27 | Receipt stored **"Low risk" when the CNN never ran** | The OOM-killed ML service degrades rather than errors, so an unchecked receipt looked exactly like a cleared one |

Defect 27 is the most serious finding in the project: **an absent verifier and a
passing verdict were indistinguishable to the user, to the database and to us.**
Verification failure is now a refusal, not a default.

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
| **[Project brochure](https://drive.google.com/file/d/1loYtGc66bu3yF7Xkgka_RDp3yvDJOA0g/view?usp=sharing)** | One-page overview of the project (PDF, Google Drive) | Reviewers, panel, anyone new to the project |

**Start Here:**
1. **New to the project?** → Read [SETUP.md](docs/SETUP.md) to get your environment running
2. **Need to understand the system?** → Read [ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. **Building an API call?** → Check [API.md](docs/API.md)
4. **Making a contribution?** → Follow [CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## Team & Branch Rules

| Member | Role | Working branch |
|---|---|---|
| Ashfaaq Feroz | Lead Dev + Chief Editor — backend, OCR, ML integration, frontend | `ashfaaq/ml-integration` |
| Arpan Chatterjee | ML Research + Dataset | `arpan/classifier` |
| Jyoti Kataria | Data + Docs | `jyoti/data-docs` |
| Ranjeet Singh | Fraud + Testing | `ranjeet/fraud-testing` |

Every member works on their own feature branch. `main` and `dev` are shared
branches, not anyone's workspace — Ashfaaq administers both in addition to
developing on `ashfaaq/ml-integration`.

### Where each member's work stands (23 Aug 2026)

| Member | Delivered | Open |
|---|---|---|
| **Ashfaaq** | Backend, OCR pipeline and Gemini key rotation, ML integration, frontend, NB 01/03, anomaly detector, all model cards, TC-26 browser run, `v1.0-fyp` release, deployment across Vercel + Render + Cloud Run | — |
| **Arpan** | `receipts_master.csv` (CORD + SROIE consolidation), NB 04 collaborative filter, NB 05 evaluation harness, standalone fake-receipt detector | Present dataset + classifier results to the advisor |
| **Jyoti** | 100 Indian receipt photos, `labels.csv` labelling, dataset README + DATA_PREP, progress report v3 | A strict 2-page executive summary if the advisor wants one (v3 is 10 pages) |
| **Ranjeet** | 100 tampered images, tampered-receipt generator, fraud test report input | Regression checklist (de-scoped at the Aug 12 freeze) |

Two attributions are corrected here rather than left implied. **NB 02 and NB 03
were completed by Ashfaaq**, not by their nominal owners, and the fraud CNN
checkpoint originally credited with AUC 0.76 was withdrawn — the file supplied
loads as EfficientNet-B0, not MobileNetV2, and scores 0.55. Every fraud number
in this repository comes from the 448px MobileNetV2 under grouped CV instead.

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
