"""
Multi-currency model experiments (Research-Programs branch only).

    research/.venv/bin/python research/models/multicurrency.py            # all experiments
    research/.venv/bin/python research/models/multicurrency.py --mode inr_only

--mode selects which models load_models() returns:
  inr_only  the v1.0-fyp binaries exactly as served (fetched by fetch_models.py
            into research/artifacts/fetched/, or ml-service/models/ as fallback)
  multi     the research variants trained here (research/artifacts/multi/)
Both stay available; nothing on main is changed.

WHAT THE REAL DATA CAN AND CANNOT SUPPORT — read before quoting any number:
  * The labelled corpus has three currencies: IDR (CORD, Indonesia), MYR (SROIE,
    Malaysia) and INR (the 100 Indian receipts). It has NO Gulf receipts, so no
    accuracy claim about SAR/AED/QAR is made anywhere. The synthetic Gulf set is
    used only for smoke tests.
  * The category split's test set is CORD + SROIE only, and currency there is a
    one-to-one proxy for the source corpus, which v1.0 deliberately excluded
    from the features. Experiment A therefore measures how much a currency
    feature lets the model shortcut on corpus identity, not a currency effect.

Outputs: research/results/models/*.md|csv|png (tracked) and research/artifacts/
(git-ignored model binaries).
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "dataset", "processed")
FX_PATH = os.path.join(REPO, "research", "config", "fx_rates.json")
OUT = os.path.join(REPO, "research", "results", "models")
ART = os.path.join(REPO, "research", "artifacts")
SEED = 42
SOURCE_CURRENCY = {"CORD": "IDR", "SROIE": "MYR"}   # everything else in the corpus is INR

sys.path.insert(0, os.path.join(REPO, "ml-service"))


def load_fx():
    with open(FX_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def to_inr(amount, currency, fx):
    """Convert with the static table, or None when the currency has no rate."""
    rate = fx["inr_per_unit"].get(currency)
    return None if rate is None else amount * rate


def load_models(mode):
    """Return the model bundle for a currency mode — the 'flag' the brief asks for."""
    import joblib
    if mode == "inr_only":
        base = os.path.join(ART, "fetched")
        if not os.path.exists(os.path.join(base, "classifier.pkl")):
            base = os.path.join(REPO, "ml-service", "models")
        return {"classifier": joblib.load(os.path.join(base, "classifier.pkl")),
                "tfidf": joblib.load(os.path.join(base, "tfidf.pkl")),
                "anomaly": joblib.load(os.path.join(base, "spending_anomaly.joblib")),
                "mode": "inr_only", "dir": base}
    base = os.path.join(ART, "multi")
    return {"classifier": joblib.load(os.path.join(base, "classifier_currency.joblib")),
            "anomaly": joblib.load(os.path.join(base, "anomaly_per_currency.joblib")),
            "mode": "multi", "dir": base}


# ── A. category classifier: text only vs text + currency ────────────────────
def experiment_classifier():
    import joblib
    import pandas as pd
    from scipy.sparse import hstack, csr_matrix
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, f1_score

    split = {s: pd.read_csv(os.path.join(DATA, f"category_{s}.csv")) for s in ("train", "test")}
    for d in split.values():
        d["currency"] = d["source"].map(SOURCE_CURRENCY).fillna("INR")
    vec = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, min_df=2)
    Xtr = vec.fit_transform(split["train"]["text"].fillna(""))
    Xte = vec.transform(split["test"]["text"].fillna(""))
    codes = sorted(set(split["train"]["currency"]) | set(split["test"]["currency"]))

    def onehot(d):
        return csr_matrix(np.array([[1.0 if c == x else 0.0 for x in codes] for c in d["currency"]]))

    rows = []
    preds = {}
    for name, (A, B) in {"text_only (v1.0 features)": (Xtr, Xte),
                         "text + currency one-hot": (hstack([Xtr, onehot(split["train"])]).tocsr(),
                                                     hstack([Xte, onehot(split["test"])]).tocsr())}.items():
        m = RandomForestClassifier(n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=SEED)
        m.fit(A, split["train"]["category_3class"])
        p = m.predict(B)
        preds[name] = p
        y = split["test"]["category_3class"]
        row = {"model": name, "test_n": len(y), "accuracy": accuracy_score(y, p),
               "macro_f1": f1_score(y, p, average="macro")}
        for c in codes:
            mask = (split["test"]["currency"] == c).values
            if mask.any():
                row[f"macro_f1_{c}"] = f1_score(y[mask], p[mask], average="macro")
        rows.append(row)
        if "currency" in name:
            os.makedirs(os.path.join(ART, "multi"), exist_ok=True)
            joblib.dump({"model": m, "tfidf": vec, "currency_codes": codes},
                        os.path.join(ART, "multi", "classifier_currency.joblib"))
    disagree = int((preds["text_only (v1.0 features)"] != preds["text + currency one-hot"]).sum())
    return rows, disagree, {c: int((split["test"]["currency"] == c).sum()) for c in codes}


# ── B. anomaly detector: reference strategies ───────────────────────────────
def experiment_anomaly():
    import joblib
    from sklearn.ensemble import IsolationForest
    from sklearn.model_selection import train_test_split
    import train_anomaly as ta          # reuse v1.0's loader, features and injection
    import anomaly as served

    rows = ta.load_transactions()
    train_rows, test_rows = train_test_split(rows, test_size=0.25, random_state=SEED)
    per_cur = defaultdict(list)
    for r in train_rows:
        per_cur[r["currency"]].append(r["amount"])
    medians = {c: float(np.median(v)) for c, v in per_cur.items()}
    inr_ref = served.POPULATION_REFERENCE_INR

    strategies = {
        # What serving does for a user with no history: one INR constant for everyone.
        "inr_only_reference": lambda r: inr_ref,
        # v1.0's training-time approach, made explicit at serving time.
        "per_currency_median": lambda r: medians.get(r["currency"], inr_ref),
    }
    results = []
    multipliers = [3, 10, 50]
    for name, ref in strategies.items():
        feat = lambda batch: np.array([[ta.build_features(r["amount"], r["category"], r["date"], ref(r))[0]]
                                       for r in batch])
        model = IsolationForest(n_estimators=ta.N_ESTIMATORS, contamination=ta.CONTAMINATION,
                                random_state=SEED, n_jobs=-1).fit(feat(train_rows))
        ta.rng = np.random.default_rng(SEED)            # identical injected sets per strategy
        injected = {m: ta.inject_outliers(test_rows, m) for m in multipliers}
        for cur in sorted({r["currency"] for r in test_rows}):
            sub = [r for r in test_rows if r["currency"] == cur]
            row = {"strategy": name, "currency": cur, "test_n": len(sub),
                   "fpr": float((model.predict(feat(sub)) == -1).mean())}
            for m in multipliers:
                inj = [r for r in injected[m] if r["currency"] == cur]
                row[f"recall@{m}x"] = float((model.predict(feat(inj)) == -1).mean()) if inj else float("nan")
            results.append(row)
        if name == "per_currency_median":
            os.makedirs(os.path.join(ART, "multi"), exist_ok=True)
            joblib.dump({"model": model, "references": medians, "features": ["log_amount_ratio"],
                         "contamination": ta.CONTAMINATION},
                        os.path.join(ART, "multi", "anomaly_per_currency.joblib"))
    return results, medians, {c: len(v) for c, v in per_cur.items()}


# ── C. reward logic: INR-only formula vs FX-normalised ──────────────────────
def experiment_rewards(fx):
    """Computed, not measured: what the v1.0 points formula pays on the synthetic
    Gulf receipts if their amounts are taken as INR, against the same receipts
    converted with the static FX table first."""
    rows = list(csv.DictReader(open(os.path.join(REPO, "dataset", "gulf_synthetic", "gulf_synthetic.csv"),
                                    encoding="utf-8")))
    out = defaultdict(lambda: {"n": 0, "inr_only": 0, "fx": 0})
    for r in rows:
        amt = float(r["total_parsed"])
        inr = to_inr(amt, r["currency"], fx)
        o = out[r["currency"]]
        o["n"] += 1
        o["inr_only"] += max(1, int(amt // 100))           # base points, as server.js
        o["fx"] += max(1, int(inr // 100)) if inr is not None else 0
    return {c: {**v, "ratio": v["fx"] / v["inr_only"]} for c, v in sorted(out.items())}


# ── D. tamper CNN on synthetic receipts (smoke test) ────────────────────────
def experiment_tamper():
    import fraud
    rows = list(csv.DictReader(open(os.path.join(REPO, "dataset", "gulf_synthetic", "gulf_synthetic.csv"),
                                    encoding="utf-8")))
    scores = []
    for r in rows:
        p = fraud.check_tamper_cnn(os.path.join(REPO, r["image_path"]))
        prob = p[1] if isinstance(p, tuple) else p
        scores.append({**{k: r[k] for k in ("currency", "language", "digits", "degradation")},
                       "tamper_probability": prob})
    return scores, fraud.TAMPER_THRESHOLD


def md_table(rows, cols, fmt=".3f"):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for r in rows:
        body += "| " + " | ".join(
            (f"{r[c]:{fmt}}" if isinstance(r.get(c), float) else str(r.get(c, ""))) for c in cols) + " |\n"
    return head + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["inr_only", "multi", "experiments"], default="experiments")
    a = ap.parse_args()
    if a.mode != "experiments":
        b = load_models(a.mode)
        print(f"loaded {a.mode} models from {os.path.relpath(b['dir'], REPO)}: "
              f"{sorted(k for k in b if k not in ('mode', 'dir'))}")
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True)
    fx = load_fx()

    cls_rows, disagree, test_counts = experiment_classifier()
    an_rows, medians, train_counts = experiment_anomaly()
    rewards = experiment_rewards(fx)
    tamper, thr = experiment_tamper()

    cls_cols = ["model", "test_n", "accuracy", "macro_f1"] + [k for k in cls_rows[0] if k.startswith("macro_f1_")]
    by_cur = defaultdict(list)
    for t in tamper:
        if t["tamper_probability"] is not None:
            by_cur[t["currency"]].append(t["tamper_probability"])
    tam_rows = [{"currency": c, "n": len(v), "flagged_at_threshold": float(np.mean([x >= thr for x in v])),
                 "median_probability": float(np.median(v)), "max_probability": float(np.max(v))}
                for c, v in sorted(by_cur.items())]

    md = ["# Multi-currency model experiments", "",
          f"FX table: `research/config/fx_rates.json` version `{fx['version']}` (static, as of {fx['as_of']}).", "",
          "## A. Category classifier — text only vs text + currency", "",
          f"Same split as v1.0 (`category_train/test.csv`). Test-set currencies: {test_counts}. "
          "**No INR and no Gulf rows exist in this split.** Currency is a one-to-one proxy for the "
          "source corpus (CORD → IDR, SROIE → MYR).", "",
          md_table(cls_rows, cls_cols),
          f"Predictions that differ between the two models: {disagree} of {cls_rows[0]['test_n']}.", "",
          "## B. Anomaly detector — reference strategy", "",
          f"Real held-out receipts (receipts_master, 25% split, seed {SEED}). Training rows per currency: "
          f"{train_counts}. Per-currency medians: { {k: round(v, 2) for k, v in medians.items()} }. "
          "Recall is against INJECTED SYNTHETIC outliers (v1.0's method).", "",
          md_table(an_rows, ["strategy", "currency", "test_n", "fpr", "recall@3x", "recall@10x", "recall@50x"]),
          "",
          "## C. Reward points — v1.0 formula vs FX-normalised (computed, not measured)", "",
          "Base points on the 48 synthetic receipts. `inr_only` takes the amount as rupees, which is "
          "what v1.0 would do. `fx` converts with the static table first.", "",
          md_table([{"currency": c, **v} for c, v in rewards.items()], ["currency", "n", "inr_only", "fx", "ratio"],
                   fmt=".2f"),
          "## D. Tamper CNN on synthetic receipts — smoke test only", "",
          f"The served 448px model at threshold {thr}. Every synthetic receipt is untampered by "
          "construction, so a flag here is a false positive **on rendered images**, which differ from "
          "camera photos. This is not a measurement of real-world behaviour.", "",
          md_table(tam_rows, ["currency", "n", "flagged_at_threshold", "median_probability", "max_probability"]),
          "## E. Recommender", "",
          "The recommender ranks offers by spend **category** and a decayed category-interest vector. "
          "Amounts and currency never enter it, so there was nothing to make currency-aware. Its offer "
          "**catalogue** is priced in ₹, which is a product limitation, not a model one.", ""]
    with open(os.path.join(OUT, "multicurrency.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(OUT, "multicurrency.json"), "w", encoding="utf-8") as fh:
        json.dump({"fx_version": fx["version"], "classifier": cls_rows, "classifier_disagree": disagree,
                   "classifier_test_counts": test_counts, "anomaly": an_rows,
                   "anomaly_medians": medians, "anomaly_train_counts": train_counts,
                   "rewards": rewards, "tamper": tam_rows, "tamper_threshold": thr},
                  fh, indent=2, default=float)
    with open(os.path.join(OUT, "anomaly_strategies.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(an_rows[0]))
        w.writeheader()
        w.writerows(an_rows)

    fig, ax = plt.subplots(figsize=(7, 3.2))
    curs = sorted({r["currency"] for r in an_rows})
    for i, strat in enumerate(["inr_only_reference", "per_currency_median"]):
        vals = [next(r["fpr"] for r in an_rows if r["strategy"] == strat and r["currency"] == c) for c in curs]
        ax.bar([j + i * 0.38 for j in range(len(curs))], vals, 0.38, label=strat,
               color=["#9aa5b1", "#3b6ea5"][i])
    ax.set_xticks([j + 0.19 for j in range(len(curs))])
    ax.set_xticklabels(curs)
    ax.set_ylabel("false-positive rate (held-out real)")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.15, color="#b0413e", lw=1, ls="--")
    ax.text(len(curs) - 0.6, 0.17, "15% budget", color="#b0413e", fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title("Anomaly flags on genuine receipts, by reference strategy", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "anomaly_fpr.png"), dpi=150)
    plt.close(fig)
    print("\n".join(md))


if __name__ == "__main__":
    main()
