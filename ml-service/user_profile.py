"""
User Interest Vector — Owner: Arpan Chatterjee
Maintains and updates a per-user spending interest vector used by the recommender.
"""

import os


def compute(user_id: str) -> dict:
    """
    TODO (Arpan):
    1. Load user's receipt history from Firestore (or local cache CSV)
    2. Aggregate total spend per category
    3. Normalise to a probability distribution (sums to 1.0)
    4. Return as { category: weight } dict
    Example: { "Groceries": 0.45, "Food & Dining": 0.30, "Electronics": 0.25 }
    """
    # TODO: implement interest vector computation
    raise NotImplementedError("compute() not yet implemented — assigned to Arpan")


def update(user_id: str, category: str, amount: float, merchant: str) -> bool:
    """
    TODO (Arpan):
    1. Load existing interest vector for user_id
    2. Apply exponential moving average update:
       new_weight = alpha * new_signal + (1 - alpha) * old_weight
       Suggested alpha = 0.1 (slow drift to avoid noise)
    3. Re-normalise weights so they sum to 1.0
    4. Persist updated vector back to Firestore
    5. Return True on success
    """
    # TODO: implement online interest vector update
    raise NotImplementedError("update() not yet implemented — assigned to Arpan")
