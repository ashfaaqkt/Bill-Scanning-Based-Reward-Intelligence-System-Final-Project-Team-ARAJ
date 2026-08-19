# Model Card — Reward Recommender

| | |
|:---|:---|
| **Modules** | `ml-service/recommend.py`, `ml-service/user_profile.py`, `ml-service/offers.py` |
| **Owners** | Arpan Chatterjee (NB 04 collaborative filter) · Ashfaaq KT (Sprint 3 implementation + wiring) |
| **Task** | Rank reward offers by relevance to a user's spending |
| **Learning type** | **Hybrid Model** — Content-based + Collaborative Filtering (SVD) |
| **Served by** | `/ml/recommend` → `/api/recommendations` and `/api/upload` |
| **Status** | ✅ **Wired, trained, and target NDCG@5 > 0.70 met (0.7984)** |

---

## Collaborative Filter SVD Integration

The collaborative filter has been built using a **Singular Value Decomposition (SVD)** model trained via Notebook 04 on the `synthetic_user_interactions.csv` dataset, which contains **772 interactions across 60 users**.

The trained model is stored at `ml-service/models/collab_filter.pkl` and is automatically loaded by the recommendation engine. 

For users with at least 2 receipts, their recommendations blend content-based category affinity and SVD collaborative predicted affinity:
- **SVD Prediction**: SVD predicts a rating on a 1–5 scale. This score is normalized to a 0–1 scale: `collab_affinity = (pred - 1.0) / 4.0`.
- **Hybrid Blend**: We blend 50% content-based category affinity (decayed and log-scaled) and 50% SVD collaborative predicted affinity.
- **Fallbacks**: If no SVD model is loaded, the system falls back to pure content-based recommendation. If the user has fewer than 2 receipts, it falls back to static popularity ranking (cold start).

## How ranking works

**Interest vector** (`user_profile.py`): each receipt adds `log1p(amount)` to its
category's weight, so one large bill cannot dominate. Existing weights decay by
**0.98 per update** on new scans, tracking current interest.

**Score** per offer, over a 12-offer catalogue tagged by spend category:

```
score = 0.75 × hybrid_affinity  +  0.25 × static_popularity
```

- For a personalised user: `hybrid_affinity = 0.5 × content_affinity + 0.5 × collab_affinity`.
- Offers tagged `general` get a neutral **⅓** affinity (so popularity acts as a tie-breaker).
- **Cold start** (fewer than 2 receipts): pure popularity order.

Each offer carries a human-readable `reason`, e.g. *"matches 56% of your recent spend"*.

## Evaluation

Evaluated offline on a 50-user test split of populated user profiles using Precision@K, Recall@K, and NDCG@K metrics (visualized in `report/assets/fig_ndcg_curve.png`).

**Performance Metrics:**
- **Mean Precision@5**: `0.3560`
- **Mean Recall@5**: `1.3167`
- **Mean NDCG@5**: `0.7984` ✅ (exceeds the target `> 0.70` by a wide margin)

**NDCG@K Curve Values:**
- NDCG@1: `0.9705`
- NDCG@2: `0.9172`
- NDCG@3: `0.8972`
- NDCG@4: `0.8263`
- NDCG@5: `0.7984`
- NDCG@6: `0.7701`
- NDCG@10: `0.8550`

## Storage

Interest vectors live in `ml-service/models/user_profiles.json` — a **derived
serving cache**, not a second database. The ml-service holds no Firestore
credentials by design; Firestore remains the source of truth. Atomic writes,
bounded to 5,000 users (least-recently-updated evicted), gitignored as user data,
and a write failure can never fail a receipt scan.

## Limitations

1. **Synthetic Training Bias**: The SVD model is trained on `synthetic_user_interactions.csv`. Collecting real user feedback logs (offer clicks and claims) in production will allow training a true, organic collaborative filter.
2. **Only 3 spend categories** flow from the OCR, so the interest vector is coarse. 5 of 12 offers are tagged `general` and rank on popularity alone.
3. **`popularity` values are hand-set product judgements**, not measured engagement.
4. **Cold start is not personalised** — a new user sees the same list as everyone else until their second receipt.

## Reproduce

No training step. Behaviour verified via:

```bash
ml-service/.venv/bin/python -c "import recommend; print(recommend.rank('user_id', 5))"
```
