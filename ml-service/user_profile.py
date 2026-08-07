"""
User Profiling — Owner: Arpan Chatterjee · Sprint 3 implementation: Ashfaaq KT
Maintain per-user spend interest vectors for personalised reward ranking.

WHERE THIS STORES DATA
Firestore remains the source of truth for receipts; the ml-service has no
Firestore credentials by design (only backend/server.js holds the service
account). So the interest vector is kept here as a small JSON file — a serving
cache derived from events the backend forwards, not a second database. Deleting
it costs nothing but a rebuild as new receipts arrive.

HOW THE VECTOR IS BUILT
Each receipt contributes its amount to its category. Older spend is decayed on
every update so the vector tracks current interest rather than lifetime totals —
a user who has switched from groceries to dining should get dining offers.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import offers

PROFILE_PATH = Path(__file__).resolve().parent / "models" / "user_profiles.json"

# Each new receipt scales existing weights by this before adding its own. At 0.98
# a category's influence roughly halves after ~35 receipts, so the vector adapts
# within a few weeks of normal use without discarding history outright.
DECAY = 0.98
MAX_USERS = 5000          # keep the cache bounded; least-recently-updated evicted

_lock = threading.Lock()
_profiles = None


# ── PERSISTENCE ────────────────────────────────────────────────
def _load():
    global _profiles
    if _profiles is not None:
        return _profiles

    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH) as handle:
                _profiles = json.load(handle)
        except Exception:
            _profiles = {}          # corrupt cache is not worth failing a scan over
    else:
        _profiles = {}
    return _profiles


def _save():
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = PROFILE_PATH.with_suffix(".json.tmp")
    with open(temp, "w") as handle:
        json.dump(_profiles, handle, indent=2)
    temp.replace(PROFILE_PATH)      # atomic, so a crash cannot truncate the cache


def _evict_if_needed():
    if len(_profiles) <= MAX_USERS:
        return
    ordered = sorted(_profiles.items(), key=lambda kv: kv[1].get("updated_at", ""))
    for user_id, _ in ordered[:len(_profiles) - MAX_USERS]:
        _profiles.pop(user_id, None)


# ── PROFILE UPDATE ENTRY POINT ─────────────────────────────────
# Called after every successful receipt scan (fire-and-forget from server.js)
def update(user_id: str, category: str, amount: float, merchant: str) -> dict:
    """
    Records a new spend event in the user's category interest vector.
    Enables the collaborative filter to improve recommendation accuracy over time.
    """
    if not user_id:
        return {"updated": False, "reason": "missing user_id"}

    try:
        amount_value = max(float(amount), 0.0)
    except (TypeError, ValueError):
        amount_value = 0.0

    bucket = offers.normalise_category(category)

    with _lock:
        profiles = _load()
        profile = profiles.setdefault(user_id, {"weights": {}, "receipts": 0})
        weights = profile["weights"]

        for key in list(weights):
            weights[key] *= DECAY

        # Amounts are log-scaled so one large receipt cannot dominate the vector.
        import math
        weights[bucket] = weights.get(bucket, 0.0) + math.log1p(amount_value)

        profile["receipts"] = profile.get("receipts", 0) + 1
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        if merchant:
            recent = profile.setdefault("recent_merchants", [])
            recent.append(str(merchant)[:80])
            profile["recent_merchants"] = recent[-10:]

        _evict_if_needed()
        try:
            _save()
        except Exception:
            pass                     # a cache write failure must not fail the scan

        return {
            "updated": True,
            "category": bucket,
            "receipts": profile["receipts"],
            "interest": _normalised(profile["weights"]),
        }


# ── READ API (used by recommend.py) ────────────────────────────
def _normalised(weights):
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {k: round(v / total, 4) for k, v in sorted(weights.items())}


def interest_vector(user_id: str) -> dict:
    """Category -> share of recent spend, summing to 1. Empty for a new user."""
    with _lock:
        profile = _load().get(user_id)
        return _normalised(profile["weights"]) if profile else {}


def receipt_count(user_id: str) -> int:
    with _lock:
        profile = _load().get(user_id)
        return int(profile.get("receipts", 0)) if profile else 0
