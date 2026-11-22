"""
Synthetic Arabic / Gulf receipt generator — research test set.

EVERYTHING THIS SCRIPT PRODUCES IS SYNTHETIC. The receipts are rendered from
templates with invented merchants and prices. They exist to exercise parsing,
the currency gate and the evaluation harness, and must never be reported as
real data or used to support an accuracy claim about real Gulf receipts.

Output (images are git-ignored and regenerated; the CSV is tracked):
  dataset/gulf_synthetic/images/gs_###.png
  dataset/gulf_synthetic/gulf_synthetic.csv

Run from the repo root:
  research/.venv/bin/python dataset/gulf_synthetic/generate.py [--n 48] [--seed 2026]

Determinism: a fixed seed gives an identical CSV on any machine. Image bytes are
identical for the same Pillow / font versions (verified by
research/tests/test_generator_determinism.py).
"""

import argparse
import csv
import hashlib
import math
import os
import random
from datetime import date, timedelta

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FONT_DIR = os.path.join(REPO, "research", "fonts")
IMAGE_DIR = os.path.join(HERE, "images")
CSV_PATH = os.path.join(HERE, "gulf_synthetic.csv")

# Column names reuse receipts_master.csv where they apply, then add the
# research columns the brief asked for.
COLUMNS = ["image_path", "merchant", "date", "total", "category", "items_text", "source",
           "total_parsed", "currency", "spend_category", "fraud_label",
           "language", "layout", "digits", "degradation", "font",
           "printed_date", "printed_total", "merchant_ar", "notes"]

EASTERN = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# (code, arabic marker, latin marker, VAT rate, VAT label en, VAT label ar)
# VAT rates as legislated: KSA 15%, UAE 5%; Qatar levies no VAT.
CURRENCIES = {
    "SAR": ("ر.س", "SAR", 0.15, "VAT 15%", "ضريبة القيمة المضافة ١٥٪"),
    "AED": ("د.إ", "AED", 0.05, "VAT 5%", "ضريبة القيمة المضافة ٥٪"),
    "QAR": ("ر.ق", "QAR", 0.0, None, None),
    "INR": (None, "₹", 0.05, "GST 5%", None),
}

# Invented merchants — none is a real business.
MERCHANTS = {
    "Supermarket / Grocery": [("Al Noor Market", "سوق النور"),
                              ("Gulf Fresh Grocery", "بقالة الخليج الطازجة")],
    "Food & Beverage": [("Desert Rose Cafe", "مقهى وردة الصحراء"),
                        ("Sahara Bakery", "مخبز الصحراء")],
    "General Retail": [("Palm Electronics", "إلكترونيات النخلة"),
                       ("Corniche Pharmacy", "صيدلية الكورنيش")],
}
INDIAN_MERCHANTS = {
    "Supermarket / Grocery": "Sharma General Store",
    "Food & Beverage": "Annapoorna Tiffin Centre",
    "General Retail": "City Medicals",
}
ITEMS = {
    "Supermarket / Grocery": [("Milk 1L", "حليب ١ لتر"), ("Dates 500g", "تمر ٥٠٠ غرام"),
                              ("Rice 5kg", "أرز ٥ كغ"), ("Eggs x12", "بيض ١٢"),
                              ("Bread", "خبز"), ("Olive Oil", "زيت زيتون")],
    "Food & Beverage": [("Arabic Coffee", "قهوة عربية"), ("Shawarma", "شاورما"),
                        ("Falafel Wrap", "لفافة فلافل"), ("Fresh Juice", "عصير طازج"),
                        ("Kunafa", "كنافة"), ("Mint Tea", "شاي بالنعناع")],
    "General Retail": [("USB Cable", "كابل يو اس بي"), ("Phone Case", "غطاء هاتف"),
                       ("Paracetamol", "باراسيتامول"), ("Sunscreen", "واقي شمس"),
                       ("Batteries AA", "بطاريات"), ("Notebook", "دفتر")],
}
PRICE_RANGE = {  # per item, in the receipt's own currency
    "SAR": (3, 120), "AED": (3, 120), "QAR": (3, 120), "INR": (20, 900),
}
AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
             "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

DEGRADATIONS = ["clean", "rotation", "blur", "low_light"]
LANG_CYCLE = ["ar", "en", "mixed"]


def font(name, size):
    files = {"naskh": "NotoNaskhArabic.ttf", "kufi": "NotoKufiArabic.ttf",
             "sans": "NotoSans.ttf", "mono": "NotoSansMono.ttf"}
    return ImageFont.truetype(os.path.join(FONT_DIR, files[name]), size)


def shape(text):
    """Arabic shaping + bidi reordering, since this Pillow build may lack raqm."""
    return get_display(arabic_reshaper.reshape(text))


def money(value, eastern):
    s = f"{value:,.2f}"
    if eastern:
        # Arabic typography: ٬ for grouping, ٫ for the decimal point.
        s = s.replace(",", "٬").replace(".", "٫").translate(EASTERN)
    return s


def printed_date(d, style, eastern):
    if style == "dmy":
        s = f"{d.day:02d}/{d.month:02d}/{d.year}"
    elif style == "iso":
        s = d.isoformat()
    else:  # Arabic month name
        s = f"{d.day} {AR_MONTHS[d.month - 1]} {d.year}"
    return s.translate(EASTERN) if eastern else s


def plan(n, seed):
    """Decide every receipt's attributes and contents. Pure function of (n, seed)."""
    rng = random.Random(seed)
    codes = ["SAR", "AED", "QAR", "INR"]
    rows = []
    for i in range(n):
        code = codes[i % 4]
        category = list(MERCHANTS)[(i // 4) % 3]
        degradation = DEGRADATIONS[(i // 12) % 4]
        if code == "INR":
            language, digits = "en", "latin"          # controls look Indian
        else:
            language = LANG_CYCLE[(i // 4) % 3]
            digits = "eastern" if (language != "en" and (i // 4) % 2 == 0) else "latin"
        eastern = digits == "eastern"

        if code == "INR":
            merchant_en, merchant_ar = INDIAN_MERCHANTS[category], ""
        else:
            merchant_en, merchant_ar = rng.choice(MERCHANTS[category])
        lo, hi = PRICE_RANGE[code]
        picks = rng.sample(ITEMS[category], rng.randint(2, 5))
        items = [(en, ar, round(rng.uniform(lo, hi), 2)) for en, ar in picks]
        subtotal = round(sum(p for _, _, p in items), 2)
        vat = round(subtotal * CURRENCIES[code][2], 2)
        total = round(subtotal + vat, 2)
        d = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
        date_style = ("arabic_month" if language == "ar" and rng.random() < 0.5
                      else rng.choice(["dmy", "iso"]) if code != "INR" else "dmy")
        use_symbol = rng.random() < 0.6
        rows.append({
            "i": i, "code": code, "category": category, "degradation": degradation,
            "language": language, "digits": digits, "merchant_en": merchant_en,
            "merchant_ar": merchant_ar, "items": items, "subtotal": subtotal, "vat": vat,
            "total": total, "date": d, "date_style": date_style, "use_symbol": use_symbol,
            "font_ar": rng.choice(["naskh", "kufi"]), "font_en": rng.choice(["sans", "mono"]),
            "rotation": rng.uniform(-7, 7), "blur": rng.uniform(1.2, 2.2),
            "light": rng.uniform(0.45, 0.65),
        })
    return rows


def currency_marker(r):
    ar_mark, latin_mark = CURRENCIES[r["code"]][0], CURRENCIES[r["code"]][1]
    if r["code"] == "INR":
        return "₹" if r["use_symbol"] else "Rs."
    if r["language"] == "en":
        return latin_mark
    return ar_mark if r["use_symbol"] else latin_mark


_CMAPS = {}


def _covers(name, text):
    """True if font `name` has a glyph for every non-space character of text."""
    if name not in _CMAPS:
        from fontTools.ttLib import TTFont
        files = {"naskh": "NotoNaskhArabic.ttf", "kufi": "NotoKufiArabic.ttf",
                 "sans": "NotoSans.ttf", "mono": "NotoSansMono.ttf"}
        _CMAPS[name] = set(TTFont(os.path.join(FONT_DIR, files[name])).getBestCmap())
    return all(ord(c) in _CMAPS[name] for c in text if not c.isspace())


def has_arabic(text):
    """Arabic LETTERS only. A string of Eastern digits and separators is a number
    and reads left to right; passing it through bidi would reorder it."""
    return any(("\u0621" <= c <= "\u064A") or ("\u0671" <= c <= "\u06D3") for c in text)


class Pen:
    """Chooses shaping and a covering font per string, preferring the receipt's fonts."""

    def __init__(self, r):
        self.order = [r["font_ar"], r["font_en"], "naskh", "sans"]

    def __call__(self, text, size):
        shown = get_display(arabic_reshaper.reshape(text)) if has_arabic(text) else text
        for name in self.order:
            if _covers(name, shown):
                return shown, font(name, size)
        return shown, font(self.order[0], size)


def render(r):
    W = 640
    eastern = r["digits"] == "eastern"
    lang = r["language"]
    pen = Pen(r)
    lines = []          # ("centre", text, size) | ("row", left, right, size)

    mark = currency_marker(r)
    pdate = printed_date(r["date"], r["date_style"], eastern)
    if lang in ("ar", "mixed") and r["merchant_ar"]:
        lines.append(("centre", r["merchant_ar"], 32))
    if lang in ("en", "mixed") or not r["merchant_ar"]:
        lines.append(("centre", r["merchant_en"], 30))
    if r["code"] == "INR":
        lines.append(("centre", "GSTIN 29ABCDE1234F1Z5", 20))
    elif r["code"] in ("SAR", "AED"):
        trn = "300000000000003" if r["code"] == "SAR" else "100000000000003"
        lines.append(("centre", "TRN " + (trn.translate(EASTERN) if eastern else trn), 20))
    lines.append(("centre", "", 12))

    if lang == "ar":
        lines.append(("row", pdate, "التاريخ", 22))
    elif lang == "mixed":
        lines.append(("row", "Date  " + pdate, "التاريخ", 22))
    else:
        lines.append(("row", "Date", pdate, 22))
    lines.append(("centre", "-" * 44, 18))

    for en, ar, price in r["items"]:
        p = money(price, eastern)
        if lang == "en":
            lines.append(("row", en, p, 22))
        elif lang == "ar":
            lines.append(("row", p, ar, 22))
        else:
            lines.append(("row", f"{en}   {p}", ar, 22))
    lines.append(("centre", "-" * 44, 18))

    vat_en, vat_ar = CURRENCIES[r["code"]][3], CURRENCIES[r["code"]][4]
    if r["vat"] > 0:
        v = money(r["vat"], eastern)
        if lang == "ar" and vat_ar:
            lines.append(("row", v, vat_ar, 22))
        else:
            lines.append(("row", vat_en, v, 22))

    total_str = money(r["total"], eastern)
    if mark in ("ر.س", "د.إ", "ر.ق"):
        printed_total = f"{total_str} {mark}"
    else:
        printed_total = f"{mark} {total_str}"
    if lang == "en":
        lines.append(("row", "TOTAL", printed_total, 28))
    else:
        lines.append(("row", printed_total, "الإجمالي", 28))
    lines.append(("centre", "", 12))
    lines.append(("centre", "شكراً لزيارتكم" if lang == "ar" else "Thank you", 22))

    H = 70 + 46 * len(lines)
    img = Image.new("RGB", (W, H), (252, 251, 247))
    draw = ImageDraw.Draw(img)
    ink = (25, 25, 25)
    y = 35
    for line in lines:
        if line[0] == "centre":
            text, f = pen(line[1], line[2])
            draw.text(((W - draw.textlength(text, font=f)) / 2, y), text, font=f, fill=ink)
        else:
            left, lf = pen(line[1], line[3])
            right, rf = pen(line[2], line[3])
            draw.text((30, y), left, font=lf, fill=ink)
            draw.text((W - 30 - draw.textlength(right, font=rf), y), right, font=rf, fill=ink)
        y += 46
    return img, printed_total, pdate


def degrade(img, r):
    if r["degradation"] == "rotation":
        img = img.rotate(r["rotation"], expand=True, fillcolor=(205, 205, 200),
                         resample=Image.BICUBIC)
    elif r["degradation"] == "blur":
        img = img.filter(ImageFilter.GaussianBlur(r["blur"]))
    elif r["degradation"] == "low_light":
        img = ImageEnhance.Brightness(img).enhance(r["light"])
        img = ImageEnhance.Contrast(img).enhance(0.8)
    return img


def generate(n=48, seed=2026, out_csv=CSV_PATH, image_dir=IMAGE_DIR, write_images=True):
    os.makedirs(image_dir, exist_ok=True)
    rows = []
    for r in plan(n, seed):
        img, printed_total, pdate = render(r)
        img = degrade(img, r)
        name = f"gs_{r['i']:03d}.png"
        if write_images:
            img.save(os.path.join(image_dir, name), optimize=False)
        rows.append({
            "image_path": f"dataset/gulf_synthetic/images/{name}",
            "merchant": r["merchant_en"],
            "date": r["date"].isoformat(),
            "total": f"{r['total']:.2f}",
            "category": r["category"],
            "items_text": ", ".join(f"{en} (x 1)" for en, _, _ in r["items"]),
            "source": "synthetic",
            "total_parsed": f"{r['total']:.2f}",
            "currency": r["code"],
            "spend_category": r["category"],
            "fraud_label": "",
            "language": r["language"],
            "layout": "bilingual_two_column" if r["language"] == "mixed" else
                      ("rtl" if r["language"] == "ar" else "ltr"),
            "digits": r["digits"],
            "degradation": r["degradation"],
            "font": f"{r['font_ar']}/{r['font_en']}",
            "printed_date": pdate,
            "printed_total": printed_total,
            "merchant_ar": r["merchant_ar"],
            "notes": "SYNTHETIC — rendered by generate.py; invented merchant and prices"
                     + ("; INR control" if r["code"] == "INR" else "")
                     + ("; no VAT (Qatar)" if r["code"] == "QAR" else ""),
        })
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return rows


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    rows = generate(a.n, a.seed)
    print(f"Wrote {len(rows)} SYNTHETIC receipts → {os.path.relpath(CSV_PATH, REPO)}")
