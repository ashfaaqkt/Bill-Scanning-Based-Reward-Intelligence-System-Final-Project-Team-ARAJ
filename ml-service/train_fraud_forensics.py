#!/usr/bin/env python3
"""
Fraud detection from hand-designed forensic features.

Evaluated under exactly the same 5-fold grouped splits as the CNN
(train_fraud_cv.py, same SEED and same source-receipt groups), so the two
AUCs are directly comparable and can be fused later.

Extracted features are cached to report/assets/forensic_features.csv — delete
that file to force re-extraction.

Run:  .torch_eval_venv/bin/python ml-service/train_fraud_forensics.py
"""

import csv
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forensics
from train_fraud_cv import load_rows, N_FOLDS, SEED, USE_NORMALIZED

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "report" / "assets"
SUFFIX = "_normalized" if USE_NORMALIZED else ""
CACHE = ASSETS / f"forensic_features{SUFFIX}.csv"


def build_feature_table(rows):
    """Extracts (or loads cached) forensic features for every labelled image."""
    if CACHE.exists():
        with open(CACHE, newline="") as handle:
            cached = {r["path"]: r for r in csv.DictReader(handle)}
        if all(r["path"] in cached for r in rows):
            names = [c for c in next(iter(cached.values())) if c not in ("path", "y", "group")]
            matrix = np.array([[float(cached[r["path"]][n]) for n in names] for r in rows],
                              dtype=np.float32)
            print(f"Loaded cached features for {len(rows)} images ({len(names)} features)")
            return matrix, names

    print(f"Extracting forensic features from {len(rows)} images...")
    start = time.time()
    records, names = [], None
    for index, row in enumerate(rows, start=1):
        features = forensics.extract_features(row["path"])
        names = names or sorted(features)
        records.append([features[n] for n in names])
        if index % 40 == 0:
            print(f"  {index}/{len(rows)}  ({time.time() - start:.0f}s)")

    matrix = np.array(records, dtype=np.float32)
    ASSETS.mkdir(parents=True, exist_ok=True)
    with open(CACHE, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "y", "group"] + names)
        for row, values in zip(rows, records):
            writer.writerow([row["path"], row["y"], row["group"]] + list(values))

    print(f"Extracted in {time.time() - start:.0f}s → cached to {CACHE.name}")
    return matrix, names


def main():
    rows = load_rows(USE_NORMALIZED)
    labels = np.array([r["y"] for r in rows])
    groups = np.array([r["group"] for r in rows])

    print(f"Dataset: {len(rows)} images "
          f"({int((labels == 0).sum())} genuine / {int((labels == 1).sum())} tampered), "
          f"{len(set(groups))} source receipts\n")

    features, names = build_feature_table(rows)
    print()

    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    fold_aucs = []
    oof = np.zeros(len(rows), dtype=np.float64)
    sources = np.array([r["source"] for r in rows])

    for fold, (train_idx, test_idx) in enumerate(
            splitter.split(features, labels, groups=groups), start=1):
        leaked = set(groups[train_idx]) & set(groups[test_idx])
        assert not leaked, f"fold {fold} leaked source receipts: {leaked}"

        model = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_depth=3,
            min_samples_leaf=8, l2_regularization=1.0, random_state=SEED)
        model.fit(features[train_idx], labels[train_idx])

        probabilities = model.predict_proba(features[test_idx])[:, 1]
        oof[test_idx] = probabilities
        auc = roc_auc_score(labels[test_idx], probabilities)
        fold_aucs.append(auc)
        print(f"Fold {fold}/{N_FOLDS} — train {len(train_idx)} / test {len(test_idx)}  "
              f"AUC {auc:.4f}")

    aucs = np.array(fold_aucs)
    mean_auc, std_auc = float(aucs.mean()), float(aucs.std(ddof=1))
    half_width = 1.96 * std_auc / np.sqrt(N_FOLDS)
    oof_auc = float(roc_auc_score(labels, oof))

    mask = sources == "indian"
    control_auc = (float(roc_auc_score(labels[mask], oof[mask]))
                   if mask.sum() and len(set(labels[mask].tolist())) == 2 else None)

    print("\n" + "=" * 62)
    print("FORENSIC FEATURES — 5-FOLD GROUPED CV")
    print("=" * 62)
    print(f"  Mean AUC        : {mean_auc:.4f} +/- {std_auc:.4f} (SD)")
    print(f"  95% CI (mean)   : [{mean_auc - half_width:.4f}, {mean_auc + half_width:.4f}]")
    print(f"  Pooled OOF AUC  : {oof_auc:.4f}")
    if control_auc is not None:
        print(f"  Source control  : {control_auc:.4f}  (indian/ only, n={int(mask.sum())})")
    print(f"\n  CNN under identical folds: pooled OOF 0.7766 / mean 0.8316")

    # Which signals actually carry the result — needed for the report.
    final = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_depth=3,
        min_samples_leaf=8, l2_regularization=1.0, random_state=SEED)
    final.fit(features, labels)
    importance = permutation_importance(final, features, labels, n_repeats=10,
                                        random_state=SEED, scoring="roc_auc")
    order = np.argsort(importance.importances_mean)[::-1]

    print("\n  Top forensic signals (permutation importance):")
    for i in order[:10]:
        print(f"    {names[i]:24s} {importance.importances_mean[i]:+.4f}")

    with open(ASSETS / f"forensic_cv_results{SUFFIX}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Metric", "Value"])
        for i, auc in enumerate(fold_aucs, start=1):
            writer.writerow([f"Fold {i} AUC", round(auc, 4)])
        writer.writerow(["Mean AUC", round(mean_auc, 4)])
        writer.writerow(["SD", round(std_auc, 4)])
        writer.writerow(["CI95 low", round(mean_auc - half_width, 4)])
        writer.writerow(["CI95 high", round(mean_auc + half_width, 4)])
        writer.writerow(["Pooled OOF AUC", round(oof_auc, 4)])
        if control_auc is not None:
            writer.writerow(["Source-control AUC", round(control_auc, 4)])
        writer.writerow(["N images", len(rows)])
        writer.writerow(["N features", len(names)])

    # Saved for Phase 3 fusion with the CNN's out-of-fold predictions.
    with open(ASSETS / f"forensic_oof_predictions{SUFFIX}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "group", "y", "forensic_prob"])
        for row, probability in zip(rows, oof):
            writer.writerow([row["path"], row["group"], row["y"], round(float(probability), 6)])

    print("\nSaved → forensic_cv_results.csv, forensic_oof_predictions.csv")


if __name__ == "__main__":
    sys.exit(main())
