# Model Card — Reward Recommender

| | |
|:---|:---|
| **Modules** | `ml-service/recommend.py`, `ml-service/user_profile.py`, `ml-service/offers.py` |
| **Owners** | Arpan Chatterjee (NB 04 collaborative filter) · Ashfaaq KT (Sprint 3 implementation + wiring) |
| **Task** | Rank reward offers by relevance to a user's spending |
| **Learning type** | **Not a trained model** — deterministic content-based ranking |
| **Served by** | `/ml/recommend` → `/api/recommendations` and `/api/upload` |
| **Status** | 🔸 **Wired and working, but the NDCG target is not met** |

---

## Be clear about what this is

This is **content-based ranking**, not the SVD collaborative filter the project
plan calls for. It scores each offer against the user's own category interest
vector. **No model is trained and no learned parameters exist.**

The collaborative filter requires Notebook 04, which is not built, and the only
interaction data available (`synthetic_user_interactions.csv`) is **synthetic**.
Reporting a collaborative-filter metric from synthetic interactions would be
meaningless — the same error that invalidated the Sprint 2 hybrid fraud run.

**The NDCG@5 > 0.70 target therefore remains open.** It belongs to the
collaborative filter and is not claimed here. `load_collaborative_model()` in
`recommend.py` is the seam where `collab_filter.pkl` plugs in; until then the API
honestly reports `model: "content-based"`.

## How ranking works

**Interest vector** (`user_profile.py`): each receipt adds `log1p(amount)` to its
category's weight, so one large bill cannot dominate. Existing weights decay by
**0.98 per update**, so the vector tracks *current* interest — a user switching
from groceries to dining starts getting dining offers within a few weeks.

**Score** per offer, over a 12-offer catalogue tagged by spend category:

```
score = 0.75 × category_affinity  +  0.25 × static_popularity
```

- `category_affinity` = the user's share of spend in that offer's category.
- Offers tagged `general` (no particular category) get a neutral **⅓** affinity —
  enough to compete on popularity, never enough to outrank a genuine match.
- **Cold start** (fewer than 2 receipts): pure popularity order.

Each offer carries a human-readable `reason`, e.g. *"matches 56% of your recent
spend"*.

## Evaluation

**None.** There is no held-out relevance data — no record of which offers users
actually clicked or claimed, so precision@k, recall@k and NDCG cannot be
computed. Verified behaviourally instead:

| Scenario | Result |
|:---|:---|
| New user, no history | Popularity order — Domino's, Zomato, BigBasket |
| 3 grocery receipts | BigBasket 0.963 → top; generic offers 0.45 |
| Mixed food + retail (44/56) | Retail offers ranked above food, matching the split |

## Storage

Interest vectors live in `ml-service/models/user_profiles.json` — a **derived
serving cache**, not a second database. The ml-service holds no Firestore
credentials by design; Firestore remains the source of truth. Atomic writes,
bounded to 5,000 users (least-recently-updated evicted), gitignored as user data,
and a write failure can never fail a receipt scan.

## Limitations

1. **No collaborative filtering.** Cannot recommend an offer a *similar* user
   liked — only offers matching the user's own history.
2. **No offline metric.** NDCG@5 is unmeasured and unmeasurable without
   interaction logs. Instrumenting claim events would fix this.
3. **Only 3 spend categories** flow from the OCR, so the interest vector is
   coarse. 5 of 12 offers are tagged `general` and rank on popularity alone.
4. **`popularity` values are hand-set product judgements**, not measured
   engagement.
5. **Cold start is not personalised** — a new user sees the same list as everyone
   else until their second receipt.

## Reproduce

No training step. Behaviour verified via:

```bash
ml-service/.venv/bin/python -c "import recommend; print(recommend.rank('user_id', 5))"
```
