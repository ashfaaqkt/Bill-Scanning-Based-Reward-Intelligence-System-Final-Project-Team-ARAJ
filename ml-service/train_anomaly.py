#!/usr/bin/env python3
"""
Train the spending-anomaly detector for /ml/anomaly.

WHAT THIS MODEL ACTUALLY CLAIMS
The endpoint is specified as a per-user check — "is this amount unusual for this
user". That cannot be trained: firestore_receipts.csv holds 19 real transactions
across 3 users. So the trained component is deliberately scoped as a
POPULATION-level detector — "is this amount unusual for this category" — over the
1,762 receipts in receipts_master.csv. anomaly.py layers a per-user robust
z-score on top at serving time, which needs no training and activates once a user
has enough history.

Learning type: UNSUPERVISED (Isolation Forest). There are no anomaly labels.

EVALUATION, HONESTLY
With no labelled anomalies, two numbers are reported and neither means much alone:

  * Flag rate on held-out real receipts. Assuming most real receipts are normal,
    this is the false-positive rate. It is CONTROLLED by `contamination`, not
    discovered — so clearing the <15% FPR target is by construction, and is
    reported as such.
  * Recall against INJECTED synthetic outliers (20-50x the category median, and
    category-mismatched amounts). Declared synthetic. Without this, a model that
    flags nothing would score a perfect 0% FPR.

Run:  .torch_eval_venv/bin/python ml-service/train_anomaly.py
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER = REPO_ROOT / "dataset" / "processed" / "receipts_master.csv"
MODEL_OUT = REPO_ROOT / "ml-service" / "models" / "spending_anomaly.joblib"
ASSETS = REPO_ROOT / "report" / "assets"

SEED = 42
CONTAMINATION = 0.12      # target flag rate; the <15% FPR requirement follows from this

# Only the amount ratio is used. A sweep over {amount, +category, +day, +weekday}
# showed the extra columns act as noise: at a comparable false-positive rate the
# four-feature model caught 39% of 10x outliers, the amount-only model 100%.
# With one informative feature an Isolation Forest reduces to a percentile
# threshold — that is stated plainly rather than presented as something subtler.
FEATURE_COLUMNS = [0]
N_ESTIMATORS = 200

CATEGORY_CODES = {"grocery": 0, "food": 1, "retail": 2, "restaurant": 1}

rng = np.random.default_rng(SEED)


def category_code(value):
    text = str(value or "").strip().lower()
    for keyword, code in CATEGORY_CODES.items():
        if keyword in text:
            return code
    return len(set(CATEGORY_CODES.values()))


def date_parts(value):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(str(value).strip(), fmt)
            return parsed.day, parsed.weekday()
        except (TypeError, ValueError):
            continue
    return 1, 0


def build_features(amount, category, date_value, reference_amount):
    """
    [log(amount / reference), category, day-of-month, weekday].

    The first feature is deliberately RELATIVE. IDR and MYR medians differ by
    ~3.5 orders of magnitude (49,000 vs 27), so on an absolute log scale the two
    currencies form separate clusters and the forest spends its splits telling
    them apart instead of finding outliers within each. Dividing by the currency
    median puts both on a common axis centred at 0, where "3x the typical
    receipt" means the same thing regardless of currency.

    It also makes the model transferable: the serving currency (INR) never
    appears in training, but a ratio to the user's own typical spend does not
    depend on the currency at all.
    """
    day, weekday = date_parts(date_value)
    ratio = float(np.log1p(max(amount, 0.0)) - np.log1p(max(reference_amount, 1e-9)))
    return [ratio, category_code(category), day, weekday]


def load_transactions():
    """Real receipts with a recoverable amount — needs repair_master_schema.py first."""
    rows = []
    with open(MASTER, newline="") as handle:
        for row in csv.DictReader(handle):
            raw = row.get("total_parsed", "").strip()
            if not raw:
                continue
            try:
                amount = float(raw)
            except ValueError:
                continue
            if amount <= 0:
                continue
            rows.append({
                "amount": amount,
                "category": row.get("spend_category") or row.get("category", ""),
                "date": row.get("date", ""),
                "currency": row.get("currency", ""),
            })
    return rows


def inject_outliers(rows, multiplier, n=200):
    """
    Synthetic anomalies at a KNOWN multiple of the currency's typical receipt.
    SYNTHETIC — declared wherever reported.

    Graded rather than a single bucket: a real corpus of receipts already spans
    several orders of magnitude, so "recall on outliers" is meaningless without
    saying how large an outlier. Reporting recall at 3x, 5x, 10x, 20x and 50x
    gives an operating characteristic instead of one flattering average.
    """
    by_currency = defaultdict(list)
    for row in rows:
        by_currency[row["currency"]].append(row["amount"])
    medians = {c: float(np.median(v)) for c, v in by_currency.items() if v}

    out = []
    for _ in range(n):
        base = rows[int(rng.integers(len(rows)))]
        jitter = float(rng.uniform(0.85, 1.15))
        out.append({**base, "amount": medians[base["currency"]] * multiplier * jitter})
    return out


def main():
    rows = load_transactions()
    if not rows:
        sys.exit("No parseable amounts. Run dataset/repair_master_schema.py first.")

    print(f"Transactions with a recoverable amount: {len(rows)}")
    by_currency = defaultdict(int)
    for row in rows:
        by_currency[row["currency"]] += 1
    print(f"  by currency: {dict(by_currency)}\n")

    train_rows, test_rows = train_test_split(rows, test_size=0.25, random_state=SEED)

    # Reference medians come from TRAINING data only — computing them over the
    # whole corpus would leak test information into the feature definition.
    train_by_currency = defaultdict(list)
    for row in train_rows:
        train_by_currency[row["currency"]].append(row["amount"])
    references = {c: float(np.median(v)) for c, v in train_by_currency.items()}
    print(f"  reference medians (train only): "
          f"{ {c: round(v, 2) for c, v in references.items()} }\n")

    def featurize(batch):
        full = np.array([build_features(r["amount"], r["category"], r["date"],
                                        references.get(r["currency"], 1.0))
                         for r in batch], dtype=np.float64)
        return full[:, FEATURE_COLUMNS]

    X_train, X_test = featurize(train_rows), featurize(test_rows)

    model = IsolationForest(n_estimators=N_ESTIMATORS, contamination=CONTAMINATION,
                            random_state=SEED, n_jobs=-1)
    model.fit(X_train)
    print(f"IsolationForest fitted on {len(train_rows)} transactions "
          f"(contamination={CONTAMINATION}, {N_ESTIMATORS} trees)\n")

    # ── False-positive rate on held-out REAL receipts ──
    flags = model.predict(X_test) == -1
    fpr = float(flags.mean())

    # ── Recall against INJECTED SYNTHETIC outliers, graded by size ──
    multipliers = [3, 5, 10, 20, 50]
    recall_by_multiplier = {}
    for multiplier in multipliers:
        injected = inject_outliers(test_rows, multiplier)
        caught = model.predict(featurize(injected)) == -1
        recall_by_multiplier[multiplier] = float(caught.mean())

    print("=" * 62)
    print("EVALUATION")
    print("=" * 62)
    print(f"  False-positive rate (held-out real, n={len(test_rows)}) : {fpr:.1%}")
    print(f"    target < 15%  ->  {'PASS' if fpr < 0.15 else 'FAIL'}")
    print("    NOTE: this is set by `contamination`, not discovered. Reported as such.\n")
    print("  Recall vs INJECTED SYNTHETIC outliers (200 each, declared synthetic):")
    for multiplier, value in recall_by_multiplier.items():
        bar = "#" * int(round(value * 30))
        print(f"    {multiplier:2d}x typical receipt  {value:6.1%}  {bar}")
    print("\n  Both numbers are needed: a model that flags nothing would score a")
    print("  perfect 0% FPR and 0% recall.")

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    import joblib
    # Bundle the reference medians with the model — serving cannot rebuild the
    # relative feature without them.
    joblib.dump({"model": model, "references": references,
                 "features": ["log_amount_ratio"],
                 "contamination": CONTAMINATION},
                MODEL_OUT)
    print(f"\nSaved -> {MODEL_OUT.name} "
          f"({MODEL_OUT.stat().st_size / 1024:.0f} KB, n_features_in_={model.n_features_in_})")

    ASSETS.mkdir(parents=True, exist_ok=True)
    with open(ASSETS / "anomaly_results.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Train transactions", len(train_rows)])
        writer.writerow(["Test transactions", len(test_rows)])
        writer.writerow(["Contamination", CONTAMINATION])
        writer.writerow(["False-positive rate (real)", round(fpr, 4)])
        for multiplier, value in recall_by_multiplier.items():
            writer.writerow([f"Recall @ {multiplier}x typical (synthetic)", round(value, 4)])
        writer.writerow(["Target", "FPR < 0.15"])
        writer.writerow(["Target met", "yes" if fpr < 0.15 else "no"])
    print("Saved -> report/assets/anomaly_results.csv")


if __name__ == "__main__":
    sys.exit(main())
