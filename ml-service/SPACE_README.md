# ARAJ ML Service

The machine-learning service behind **Bill Scanning Based Reward & Intelligence
System** — a BITS Pilani Digital capstone project by Team ARAJ, undertaken under
the **AI/ML** genre.

This service is where the project's actual subject lives: receipt extraction,
spend categorisation, tamper detection, duplicate detection, spending-anomaly
scoring and reward ranking. It is an **internal HTTP API, not a user-facing
app** — there is no page to visit here. The web client that demonstrates it
lives at **[araj-capstone.vercel.app](https://araj-capstone.vercel.app)**.

## Where this runs

**Google Cloud Run** — `https://araj-ml-service-1012478382071.asia-southeast1.run.app`

| Setting | Value |
|---|---|
| Region | `asia-southeast1` |
| Memory | 2 GB |
| Instances | min 0, max 2 |
| Concurrency | 8 |
| Build | `cloudbuild.yaml` at the repository root |
| Container | `ml-service/Dockerfile`, `python:3.13-slim`, gunicorn 2 workers × 4 threads |

`min instances = 0` means the service scales to zero and **cold-starts on the
first request after an idle period**. That is deliberate — it keeps the service
inside the free tier, at the cost of a slow first upload.

### How it got here — Render, then Hugging Face, then Cloud Run

The path matters more than the destination, because the first failure was silent.

**Render was first**, for the whole stack: one blueprint file, one provider, no
container work. The backend is Node, fits the free tier, and **still runs
there**. The ML service could not stay. Free Render web services are capped at
**512 MB**, and torch alone is ~250 MB resident before the tamper checkpoint
loads, with OpenCV, pandas and scikit-learn on top. Render recorded *"Instance
failed"* at 20:11 on 22 Aug 2026 — the same minute the backend logged the fraud,
profile and recommend calls as unreachable.

> **The service died and nothing said so.** All three calls degrade rather than
> error, so uploads kept succeeding and receipts were written as **Low risk with
> the 0.05 fraud baseline, no signals and no perceptual hash**. A receipt that
> had never been checked looked exactly like one that had passed. The upload
> path now refuses when verification is unavailable rather than defaulting to a
> pass.

Render's private network is also unavailable between free web services, so the
internal address failed with `getaddrinfo ENOTFOUND araj-ml-service` and had to
become a public URL.

**Hugging Face Spaces was tried next** and the service was containerised for it —
that is where `ml-service/Dockerfile` comes from. It was dropped once the tier
that actually met the service's requirements turned out to be a paid one.

**Cloud Run took it.** 2 GB is comfortably clear of the ceiling, and the tamper
CNN returns real probabilities there. The build is defined in `cloudbuild.yaml`
rather than in the Cloud Console, because a console Dockerfile-type trigger
builds and pushes but never deploys — which produced a green build sitting
behind a placeholder image.

**Why not Cloud Run from the beginning?** Render was the cheaper bet: the entire
stack was expressible in a single blueprint with no Dockerfile at all. The
constraint was invisible until runtime — the service came up, passed its health
check, and only died when `/ml/fraud-score` first imported torch under a real
upload, so nothing at planning time indicated 2 GB was needed. And Cloud Run's
setup cost — Dockerfile, Artifact Registry, a Cloud Build pipeline, a
billing-enabled project — only paid for itself once a container existed, which
is exactly what the Hugging Face attempt produced.

The container still binds `${PORT:-7860}`, so the same image runs unchanged on
Cloud Run (which injects `PORT=8080`) or on a Hugging Face Space (which expects
7860).

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

Weights are pulled at **build time** from the `v1.0-fyp` release of the project
repository — they are gitignored by design, so the image builds them in rather
than carrying them in source control. `fetch_models.py` exits non-zero when a
required binary is missing, which fails the build loudly instead of deploying a
service whose fraud model is quietly dead and returning 0.05 for everything.

| Model | Result |
|---|---|
| Category classifier | test macro-F1 **0.942** |
| Tamper CNN | AUC **0.805** pooled, **0.864** on real photographed receipts |
| Anomaly detector | FPR **13.2%** |

The tamper CNN is **below its 0.90 target** and documented as such. Two
unrelated methods plateau at the same level, which is evidence about the size of
the corpus rather than the architecture. Full detail and limitations:
[`report/model_cards/`](../report/model_cards/README.md).

## Configuration

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY_1` | **yes** | OCR returns `GEMINI_API_KEY_MISSING` without it |
| `GEMINI_API_KEY_2..N` | no | Additional keys rotate; the free-tier limit is **per project**, so keys from separate projects multiply the ceiling |
| `GEMINI_PAID_KEYS` | no | Names the keys on a billed plan so they are tried first and skip the 23-second free-tier spacing. Key 1 has been billed since 19 Aug 2026 |
| `MODEL_BASE_URL` | no | Defaults to the `v1.0-fyp` release assets |
| `PORT` | injected | Cloud Run sets 8080; falls back to 7860 |

Set secrets through the platform — Cloud Run environment variables or Secret
Manager — **never in the image**.

Billing removes the 429 quota errors. It does **not** remove 503 "model
overloaded" responses; that is Google's shared capacity, and `ocr.py` handles it
by rotating across keys and models and cooling a model that 503s for 120 seconds.
