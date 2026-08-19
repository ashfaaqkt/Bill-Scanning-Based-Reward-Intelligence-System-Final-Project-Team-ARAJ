"""
Reward Recommendations — Owner: Arpan Chatterjee · Sprint 3 implementation: Ashfaaq KT
Ranks reward offers by how well they match a user's spend profile.

WHAT THIS IS, AND WHAT IT IS NOT
This is **content-based** ranking: it scores each offer against the user's own
category interest vector (user_profile.py). It is NOT the SVD collaborative
filter — that requires a trained user x category factorisation from Notebook 04,
which does not exist yet, and the only interaction data available
(synthetic_user_interactions.csv) is synthetic. Reporting a collaborative-filter
result from synthetic interactions would be meaningless.

`load_collaborative_model()` below is the seam where the trained model plugs in:
when collab_filter.pkl appears, its predicted affinity blends with the
content-based score and the blend is reported honestly.

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
    Loads Notebook 04's SVD model if it has been trained. Returns None until then,
    which is the current state — recommendations stay content-based.
    """
    global _collab_model, _collab_load_attempted

    if _collab_load_attempted:
        return _collab_model
    _collab_load_attempted = True

    if not COLLAB_MODEL_PATH.exists():
        return None

    try:
        import joblib
        _collab_model = joblib.load(COLLAB_MODEL_PATH)
    except Exception:
        _collab_model = None
    return _collab_model


def _score(offer, interest, personalised, user_id=None):
    """Blend of category affinity and static popularity, both already 0–1."""
    affinity = interest.get(offer["category"], 0.0) if personalised else 0.0

    # A `general` offer serves no spend category, so it would otherwise always
    # score zero affinity and be permanently buried.
    if offer["category"] == offers.GENERAL:
        affinity = GENERAL_AFFINITY

    # Blend with SVD collaborative filter if available
    collab_model = load_collaborative_model()
    if personalised and collab_model is not None and user_id is not None:
        try:
            # SVD predict(user_id, item_id)
            pred = collab_model.predict(user_id, offer["category"]).est
            # Normalize 1-5 rating scale to 0-1
            collab_affinity = (pred - 1.0) / 4.0
            # Clip to 0-1 range to be safe
            collab_affinity = max(0.0, min(1.0, collab_affinity))
            # Blend weight: 50% content-based affinity, 50% collaborative-based affinity
            affinity = 0.5 * affinity + 0.5 * collab_affinity
        except Exception:
            pass

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
