"""
Reward offer catalogue — Owner: Ashfaaq KT

The offers the user can claim, tagged with the spend category each one serves so
that recommend.py can rank them against a user's interest vector. Mirrors the
pool in frontend/public/script.js; the frontend keeps its own copy as a fallback
for when the ML service is unreachable.

Categories match what the OCR prompt emits — 'Supermarket / Grocery',
'Food & Beverage', 'General Retail' — plus `general`, for offers that serve no
particular spend category and therefore rank on popularity alone.
"""

GROCERY = "grocery"
FOOD = "food"
RETAIL = "retail"
GENERAL = "general"

# `popularity` is a static prior in 0–1, used for cold-start ordering and as a
# tie-breaker. It is a product decision, not a learned quantity.
CATALOGUE = [
    {"id": "bigbasket", "icon": "🛒", "title": "BigBasket Voucher",
     "offer": "Flat ₹150 OFF on groceries", "category": GROCERY, "popularity": 0.85},
    {"id": "dominos", "icon": "🍕", "title": "Domino's Voucher",
     "offer": "Get ₹200 OFF on orders above ₹499", "category": FOOD, "popularity": 0.90},
    {"id": "bookmyshow", "icon": "🎬", "title": "BookMyShow Pass",
     "offer": "Buy 1 Get 1 movie ticket", "category": GENERAL, "popularity": 0.80},
    {"id": "starbucks", "icon": "☕", "title": "Starbucks Coupon",
     "offer": "Free Tall Beverage", "category": FOOD, "popularity": 0.70},
    {"id": "myntra", "icon": "🛍️", "title": "Myntra Voucher",
     "offer": "Flat ₹300 OFF on fashion", "category": RETAIL, "popularity": 0.75},
    {"id": "uber", "icon": "🚕", "title": "Uber Credits",
     "offer": "₹250 ride credits", "category": GENERAL, "popularity": 0.65},
    {"id": "amazon_books", "icon": "📚", "title": "Amazon Books",
     "offer": "₹180 OFF on books", "category": RETAIL, "popularity": 0.55},
    {"id": "zomato", "icon": "🍔", "title": "Zomato Gold",
     "offer": "₹220 OFF food order", "category": FOOD, "popularity": 0.88},
    {"id": "spotify", "icon": "🎧", "title": "Spotify Premium",
     "offer": "2 months premium access", "category": GENERAL, "popularity": 0.60},
    {"id": "paytm", "icon": "🧾", "title": "Paytm Cashback",
     "offer": "₹100 instant cashback", "category": GENERAL, "popularity": 0.72},
    {"id": "oyo", "icon": "🏨", "title": "OYO Voucher",
     "offer": "₹400 OFF hotel booking", "category": GENERAL, "popularity": 0.50},
    {"id": "croma", "icon": "💻", "title": "Croma Gift Card",
     "offer": "₹350 OFF electronics", "category": RETAIL, "popularity": 0.62},
    # Added 21 Aug to widen the vault. Weighted towards grocery and food, which
    # were thin: only two grocery offers served the category carrying the ×1.2
    # reward multiplier, so a grocery-heavy user saw the same voucher every time.
    {"id": "dmart", "icon": "🏬", "title": "DMart Voucher",
     "offer": "₹200 OFF on a ₹1,500 shop", "category": GROCERY, "popularity": 0.83},
    {"id": "blinkit", "icon": "⚡", "title": "Blinkit Credits",
     "offer": "₹120 OFF instant grocery delivery", "category": GROCERY, "popularity": 0.78},
    {"id": "reliance_fresh", "icon": "🥬", "title": "Reliance Fresh",
     "offer": "₹100 OFF on fruits & vegetables", "category": GROCERY, "popularity": 0.68},
    {"id": "swiggy", "icon": "🛵", "title": "Swiggy Voucher",
     "offer": "₹150 OFF on orders above ₹349", "category": FOOD, "popularity": 0.87},
    {"id": "chaayos", "icon": "🍵", "title": "Chaayos Coupon",
     "offer": "Buy 1 Get 1 on all chai", "category": FOOD, "popularity": 0.64},
    {"id": "haldirams", "icon": "🍬", "title": "Haldiram's Treat",
     "offer": "₹100 OFF on sweets & snacks", "category": FOOD, "popularity": 0.61},
    {"id": "ajio", "icon": "👗", "title": "AJIO Voucher",
     "offer": "Flat ₹400 OFF on fashion", "category": RETAIL, "popularity": 0.73},
    {"id": "decathlon", "icon": "🏸", "title": "Decathlon Card",
     "offer": "₹250 OFF on sportswear", "category": RETAIL, "popularity": 0.58},
    {"id": "apollo", "icon": "💊", "title": "Apollo Pharmacy",
     "offer": "₹150 OFF on medicines above ₹800", "category": GENERAL, "popularity": 0.66},
    {"id": "irctc", "icon": "🚆", "title": "IRCTC Travel Credit",
     "offer": "₹300 OFF on train bookings", "category": GENERAL, "popularity": 0.54},
]


def normalise_category(value):
    """Maps an OCR/classifier category string onto a catalogue category."""
    text = str(value or "").strip().lower()
    if "grocery" in text or "supermarket" in text:
        return GROCERY
    if "food" in text or "beverage" in text or "restaurant" in text:
        return FOOD
    if "retail" in text or "shopping" in text:
        return RETAIL
    return GENERAL
