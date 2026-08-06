#!/usr/bin/env python3
"""
Fuse the fraud signals into one score.

Two fusion methods are reported, deliberately:

  1. Rank-average of the CNN and forensic out-of-fold probabilities.
     No meta-model is trained, so there is no stacking leakage of any kind.
     This is the number to quote.

  2. A learned stacker over [cnn_prob + 31 forensic features + pHash distance],
     under the same grouped folds. Slightly optimistic — the CNN probabilities
     used as training features came from models that had seen the test fold —
     so it is reported as an upper bound, not as the headline.

Prerequisites (run these first, both with --normalized):
    train_fraud_cv.py --normalized          -> cnn_oof_predictions_normalized.csv
    train_fraud_forensics.py --normalized   -> forensic_oof_predictions_normalized.csv

Run:  .torch_eval_venv/bin/python ml-service/train_fraud_fusion.py --normalized
"""

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_fraud_cv import load_rows, N_FOLDS, SEED, USE_NORMALIZED

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "report" / "assets"
SUFFIX = "_normalized" if USE_NORMALIZED else ""

PHASH_SIZE = 8


def load_oof(filename, column):
    """path -> probability, from a saved out-of-fold prediction file."""
    path = ASSETS / filename
    if not path.exists():
        sys.exit(f"Missing {filename}. Run the prerequisite script first (see docstring).")
    with open(path, newline="") as handle:
        return {r["path"]: float(r[column]) for r in csv.DictReader(handle)}


def load_forensic_features(rows):
    """Cached forensic feature matrix, aligned to rows."""
    path = ASSETS / f"forensic_features{SUFFIX}.csv"
    with open(path, newline="") as handle:
        cached = {r["path"]: r for r in csv.DictReader(handle)}
    names = [c for c in next(iter(cached.values())) if c not in ("path", "y", "group")]
    matrix = np.array([[float(cached[r["path"]][n]) for n in names] for r in rows],
                      dtype=np.float32)
    return matrix, names


def phash(image_path):
    """Perceptual hash as a bit vector — same DCT construction fraud.py relies on."""
    from PIL import Image
    from scipy.fftpack import dct

    with Image.open(image_path) as handle:
        small = handle.convert("L").resize((PHASH_SIZE * 4, PHASH_SIZE * 4), Image.LANCZOS)
    pixels = np.asarray(small, dtype=np.float32)
    coefficients = dct(dct(pixels, axis=0, norm="ortho"), axis=1, norm="ortho")
    block = coefficients[:PHASH_SIZE, :PHASH_SIZE]
    return (block > np.median(block)).flatten()


def auc_or_nan(y, scores):
    return float(roc_auc_score(y, scores)) if len(set(y.tolist())) == 2 else float("nan")


def main():
    rows = load_rows(USE_NORMALIZED)
    y = np.array([r["y"] for r in rows])
    groups = np.array([r["group"] for r in rows])
    sources = np.array([r["source"] for r in rows])

    cnn_map = load_oof(f"cnn_oof_predictions{SUFFIX}.csv", "cnn_prob")
    forensic_map = load_oof(f"forensic_oof_predictions{SUFFIX}.csv", "forensic_prob")
    cnn = np.array([cnn_map[r["path"]] for r in rows])
    forensic = np.array([forensic_map[r["path"]] for r in rows])

    print(f"Dataset: {len(rows)} images ({int((y == 0).sum())} genuine / "
          f"{int((y == 1).sum())} tampered), {len(set(groups))} source receipts")
    print(f"Compression-normalized: {USE_NORMALIZED}\n")

    # ── How independent are the two models, really? ──
    correlation = spearmanr(cnn, forensic).statistic
    disagree = np.mean((cnn >= 0.5) != (forensic >= 0.5))
    print("=" * 62)
    print("SIGNAL INDEPENDENCE")
    print("=" * 62)
    print(f"  Spearman correlation (CNN vs forensic) : {correlation:+.4f}")
    print(f"  Disagreement rate at threshold 0.5     : {disagree:.1%}")
    print("  (Low correlation => fusion has something to gain)\n")

    # ── Method 1: rank-average. No meta-model, no leakage. ──
    cnn_rank = rankdata(cnn) / len(cnn)
    forensic_rank = rankdata(forensic) / len(forensic)

    print("=" * 62)
    print("ABLATION — pooled out-of-fold AUC over all images")
    print("=" * 62)
    results = {
        "CNN alone": auc_or_nan(y, cnn),
        "Forensics alone": auc_or_nan(y, forensic),
        "Rank-average fusion": auc_or_nan(y, cnn_rank + forensic_rank),
        "Weighted 0.7/0.3": auc_or_nan(y, 0.7 * cnn_rank + 0.3 * forensic_rank),
        "Probability mean": auc_or_nan(y, (cnn + forensic) / 2),
    }
    for name, value in results.items():
        print(f"  {name:24s} {value:.4f}")

    control = sources == "indian"
    print(f"\n  Source-control subset (indian/ only, n={int(control.sum())}):")
    for name, scores in (("CNN alone", cnn), ("Forensics alone", forensic),
                         ("Rank-average fusion", cnn_rank + forensic_rank)):
        print(f"    {name:22s} {auc_or_nan(y[control], scores[control]):.4f}")

    # ── Method 2: learned stacker (upper bound) ──
    features, names = load_forensic_features(rows)

    print(f"\n  Computing pHash distances...")
    hashes = np.array([phash(r["path"]) for r in rows])

    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    stacked = np.zeros(len(rows))

    for train_idx, test_idx in splitter.split(features, y, groups=groups):
        # Nearest-neighbour pHash distance, measured only against training images
        # so no test-fold information leaks in.
        distances = np.array([
            (hashes[train_idx] != hashes[i]).sum(axis=1).min() for i in range(len(rows))
        ], dtype=np.float32).reshape(-1, 1)

        stack_features = np.hstack([cnn.reshape(-1, 1), features, distances])
        model = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_depth=3,
            min_samples_leaf=8, l2_regularization=1.0, random_state=SEED)
        model.fit(stack_features[train_idx], y[train_idx])
        stacked[test_idx] = model.predict_proba(stack_features[test_idx])[:, 1]

    stacked_auc = auc_or_nan(y, stacked)
    print(f"\n  Learned stacker (upper bound) : {stacked_auc:.4f}")
    print(f"    on source-control subset     : {auc_or_nan(y[control], stacked[control]):.4f}")

    # ── Save ──
    ASSETS.mkdir(parents=True, exist_ok=True)
    with open(ASSETS / f"fusion_results{SUFFIX}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Method", "Pooled OOF AUC", "Source-control AUC"])
        writer.writerow(["CNN alone", round(results["CNN alone"], 4),
                         round(auc_or_nan(y[control], cnn[control]), 4)])
        writer.writerow(["Forensics alone", round(results["Forensics alone"], 4),
                         round(auc_or_nan(y[control], forensic[control]), 4)])
        writer.writerow(["Rank-average fusion", round(results["Rank-average fusion"], 4),
                         round(auc_or_nan(y[control], (cnn_rank + forensic_rank)[control]), 4)])
        writer.writerow(["Learned stacker (upper bound)", round(stacked_auc, 4),
                         round(auc_or_nan(y[control], stacked[control]), 4)])
        writer.writerow(["Spearman correlation", round(float(correlation), 4), ""])
        writer.writerow(["N images", len(rows), ""])

    print(f"\nSaved → report/assets/fusion_results{SUFFIX}.csv")


if __name__ == "__main__":
    sys.exit(main())
