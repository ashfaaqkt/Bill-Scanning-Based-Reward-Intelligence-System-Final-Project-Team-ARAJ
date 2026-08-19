"""
Reward Recommendations — Owner: Arpan Chatterjee · Sprint 3 implementation: Ashfaaq KT
Ranks reward offers by how well they match a user's spend profile.

WHAT THIS IS, AND WHAT IT IS NOT
Ranking is content-based at its core: each offer is scored against the user's own
category interest vector (user_profile.py). When Notebook 04's exported SVD
factors are present, a collaborative estimate is blended in at equal weight and
the response reports `model: "collaborative+content"`.

READ THE COLLABORATIVE PART WITH CARE. The factorisation is trained on
synthetic_user_interactions.csv, where the rating is a deterministic function of
a preference the generator itself assigned, across only three spend categories.
A strong offline score on that data measures the generator, not this ranker, so
no NDCG target is claimed from it — see report/model_cards/recommender.md. The
blend is wired and correct; what it is worth awaits real interaction data.

Cold start: a user with no receipts gets the catalogue ordered by popularity.
"""

from pathlib import Path

import offers
import user_profile

COLLAB_MODEL_PATH = Path(__file__).resolve().parent / "models" / "collab_filter.pkl"

# Content affinity dominates once we know the user; popularity breaks ties and
# carries the `general` offers that match no particular spend category.
WEIGHT_AFFINITY = 0.75
WEIGHT_POPULARITY = 0.25

# Below this many receipts the interest vector is too thin to trust on its own.
MIN_RECEIPTS_FOR_PERSONALISATION = 2

# Affinity granted to a `general` offer, which serves no particular spend
# category. Set to one-third — the neutral share across the three spend
# categories — so it competes fairly but never outranks a genuine category match.
# (Using the mean of the interest vector is wrong: for a single-category user the
# mean is 1.0, which let generic offers beat real matches.)
GENERAL_AFFINITY = 1 / 3

_collab_model = None
_collab_load_attempted = False


def load_collaborative_model():
    """
    Loads Notebook 04's exported SVD factors if they exist. Returns None
    otherwise, in which case recommendations stay content-based.

    Notebook 04 exports plain arrays rather than a pickled Surprise estimator on
    purpose. Unpickling the estimator would require `surprise` to be installed
    wherever this service runs, and that import failing is silent here — the
    except below would swallow it and the service would serve content-based
    rankings while appearing to have a collaborative model. Arrays keep serving
    dependency-free; see collab_predict() for the arithmetic.
    """
    global _collab_model, _collab_load_attempted

    if _collab_load_attempted:
        return _collab_model
    _collab_load_attempted = True

    if not COLLAB_MODEL_PATH.exists():
        return None

    try:
        import joblib
        bundle = joblib.load(COLLAB_MODEL_PATH)
    except Exception as exc:
        print(f"recommend.py: collaborative model failed to load ({exc}) — "
              f"ranking stays content-based")
        return None

    if not (isinstance(bundle, dict) and bundle.get("kind") == "svd_factors"):
        # A pickled Surprise estimator, or anything else we cannot evaluate
        # without extra dependencies. Refuse it loudly instead of half-using it.
        print("recommend.py: collab_filter.pkl is not an exported factor bundle "
              "— re-run Notebook 04 step 4; ranking stays content-based")
        return None

    _collab_model = bundle
    return _collab_model


def collab_predict(bundle, user_id, category):
    """
    Reproduces Surprise's SVD estimate with numpy only:

        est = global_mean + bu[u] + bi[i] + dot(qi[i], pu[u])

    An unseen user or category simply drops its term, which is what Surprise
    does too. Notebook 04 asserts this matches the trained estimator before it
    writes the bundle out.
    """
    import numpy as np

    est = bundle["global_mean"]
    u = bundle["uid_map"].get(str(user_id))
    i = bundle["iid_map"].get(str(category))

    if u is None and i is None:
        return None                      # nothing learned about either side

    if u is not None:
        est += float(bundle["bu"][u])
    if i is not None:
        est += float(bundle["bi"][i])
    if u is not None and i is not None:
        est += float(np.dot(bundle["qi"][i], bundle["pu"][u]))

    lo, hi = bundle.get("rating_scale", (1, 5))
    return min(hi, max(lo, est))


def _score(offer, interest, personalised, user_id=None):
    """Blend of category affinity and static popularity, both already 0–1."""
    affinity = interest.get(offer["category"], 0.0) if personalised else 0.0

    # A `general` offer serves no spend category, so it would otherwise always
    # score zero affinity and be permanently buried.
    if offer["category"] == offers.GENERAL:
        affinity = GENERAL_AFFINITY

    # Blend in the collaborative estimate when Notebook 04's factors are present.
    collab_model = load_collaborative_model()
    if personalised and collab_model is not None and user_id is not None:
        try:
            pred = collab_predict(collab_model, user_id, offer["category"])
            if pred is not None:
                # Rating scale 1-5 -> 0-1, matching the content affinity range.
                collab_affinity = max(0.0, min(1.0, (pred - 1.0) / 4.0))
                affinity = 0.5 * affinity + 0.5 * collab_affinity
        except Exception:
            pass    # a broken bundle must never take down a recommendation

    if not personalised:
        return offer["popularity"], "popular with other users"

    total = WEIGHT_AFFINITY * affinity + WEIGHT_POPULARITY * offer["popularity"]
    share = interest.get(offer["category"], 0.0)
    if share >= 0.4:
        reason = f"matches {int(round(share * 100))}% of your recent spend"
    elif share > 0:
        reason = f"related to {int(round(share * 100))}% of your recent spend"
    else:
        reason = "popular with other users"
    return total, reason


# ── INFERENCE ENTRY POINT ──────────────────────────────────────
# Called by /ml/recommend route; returns offers ranked by predicted affinity
def rank(user_id: str, top_n: int = 5) -> dict:
    """
    Returns the top-N reward offers most relevant to the user's spend history.
    Content-based today; blends in the collaborative filter once NB 04 ships it.
    """
    try:
        limit = max(1, min(int(top_n), len(offers.CATALOGUE)))
    except (TypeError, ValueError):
        limit = 5

    interest = user_profile.interest_vector(user_id) if user_id else {}
    receipts = user_profile.receipt_count(user_id) if user_id else 0
    personalised = bool(interest) and receipts >= MIN_RECEIPTS_FOR_PERSONALISATION

    scored = []
    for offer in offers.CATALOGUE:
        value, reason = _score(offer, interest, personalised, user_id)
        scored.append({**{k: offer[k] for k in ("id", "icon", "title", "offer", "category")},
                       "score": round(float(value), 4), "reason": reason})

    scored.sort(key=lambda item: (-item["score"], item["title"]))

    return {
        "recommendations": scored[:limit],
        "personalised": personalised,
        "receipts_seen": receipts,
        "interest": interest,
        "model": "collaborative+content" if load_collaborative_model() else "content-based",
    }
