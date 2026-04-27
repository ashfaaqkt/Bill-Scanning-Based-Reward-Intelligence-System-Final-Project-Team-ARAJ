"""
Reward Recommender — Owner: Arpan Chatterjee
Ranks reward offers for a user based on their interest vector and spending history.
"""

import os


def rank(user_id: str, top_n: int = 5) -> list:
    """
    TODO (Arpan):
    1. Load user's interest vector from user_profile.compute(user_id)
    2. Load available reward offers catalogue (CSV or Firestore collection)
    3. Score each offer against the user's interest vector:
       - Option A: cosine similarity between offer tags and user category weights
       - Option B: collaborative filter via scikit-surprise SVD
         (train on receipts_master.csv user × category spend matrix)
    4. Sort offers by score descending, return top_n
    5. Return list of { "offer_id": str, "title": str, "score": float }
    See notebook 04 for collaborative filter training experiments.
    """
    # TODO: implement reward ranker
    raise NotImplementedError("rank() not yet implemented — assigned to Arpan")
