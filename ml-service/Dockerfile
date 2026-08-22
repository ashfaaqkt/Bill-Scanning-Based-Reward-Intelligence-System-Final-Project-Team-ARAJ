# ML service container — built for Hugging Face Spaces (Docker SDK).
#
# Why not Render: the free tier caps a service at 512 MB, and this image is
# past that before the model loads -- torch is ~250 MB resident, plus OpenCV,
# pandas and scikit-learn. On 22 Aug 2026 the Render instance was killed the
# moment /ml/fraud-score first imported torch, which surfaced to the backend as
# "ML Service (Fraud) unreachable" and silently downgraded every receipt to the
# 0.05 baseline. A Space gives 16 GB, so the tamper CNN can actually run.
#
# Spaces serve on 7860 and run the container as uid 1000, so both are set here
# rather than left to default.

FROM python:3.13-slim

# libgomp is required by torch and scikit-learn at import time; the slim base
# does not carry it and the failure is a bare "libgomp.so.1: cannot open
# shared object file" at startup.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/user/.cache

WORKDIR /app

# Requirements first, so a source-only change does not re-download torch.
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

# Model binaries are gitignored by design, so the image has none until this
# runs. fetch_models.py exits non-zero when a required model is missing, which
# fails the build loudly rather than shipping a service whose fraud model is
# silently dead. MODEL_BASE_URL defaults to the v1.0-fyp release.
RUN python fetch_models.py

EXPOSE 7860

# Two workers is safe here in a way it never was on Render: each loads its own
# copy of torch, which is fine against 16 GB. Long timeout because a cold
# Gemini call measured 31 s and the 448px CNN pass sits on top of it.
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "180", \
     "--bind", "0.0.0.0:7860", "app:app"]
