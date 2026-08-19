#!/usr/bin/env python3
"""
Learning curve — does collecting more receipts actually help?

Answers the question empirically instead of by intuition. For each training-set
fraction, the model is retrained under the same 5-fold grouped protocol, but with
only that fraction of the *source receipts* available for training. Test folds are
always kept at full size, so every point on the curve is measured against the same
yardstick and the AUCs are directly comparable.

Subsampling is by source receipt, not by image: three tampered variants of one
receipt carry little more information than one, so dropping images rather than
receipts would overstate how much data the model really has.

Reading the result:
  curve still climbing at 100%  -> more receipts will raise AUC
  curve flattening at 100%      -> more of the same data will not help

Runs at 224x224 for speed. The shape of the curve, not the absolute values, is
what carries the answer; the champion model is trained at 448.

Run:  .torch_eval_venv/bin/python -u ml-service/learning_curve.py --normalized
"""

import csv
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_fraud_cv import (
    DEVICE, EPOCHS, FREEZE_EPOCHS, PATIENCE, LR_HEAD, LR_FINETUNE, WEIGHT_DECAY,
    BATCH_SIZE, N_FOLDS, SEED, TRAIN_TF, EVAL_TF, ReceiptDataset, USE_NORMALIZED,
    build_model, set_backbone_frozen, predict, load_rows,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "report" / "assets"

FRACTIONS = [0.3, 0.5, 0.7, 0.85, 1.0]
REPEATS = 2          # two subsample draws per fraction, averaged, to damp noise


def train_once(train_rows, test_rows):
    """One fold. Returns held-out probabilities for test_rows."""
    train_loader = DataLoader(ReceiptDataset(train_rows, TRAIN_TF),
                              batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(ReceiptDataset(test_rows, EVAL_TF), batch_size=BATCH_SIZE)

    model = build_model()
    set_backbone_frozen(model, True)

    counts = np.bincount([r["y"] for r in train_rows], minlength=2)
    weights = torch.tensor(counts.sum() / (2.0 * np.maximum(counts, 1)),
                           dtype=torch.float32, device=DEVICE)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                            lr=LR_HEAD, weight_decay=WEIGHT_DECAY)

    best_auc, best_probs, stale = -1.0, None, 0
    for epoch in range(1, EPOCHS + 1):
        if epoch == FREEZE_EPOCHS + 1:
            set_backbone_frozen(model, False)
            optimizer = optim.AdamW(model.parameters(), lr=LR_FINETUNE,
                                    weight_decay=WEIGHT_DECAY)
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            criterion(model(images), labels).backward()
            optimizer.step()

        labels_out, probs = predict(model, test_loader)
        auc = roc_auc_score(labels_out, probs) if len(set(labels_out.tolist())) == 2 else 0.5
        if auc > best_auc:
            best_auc, best_probs, stale = auc, probs, 0
        else:
            stale += 1
            if stale >= PATIENCE:
                break
    return best_probs


def main():
    rows = load_rows(USE_NORMALIZED)
    y = np.array([r["y"] for r in rows])
    groups = np.array([r["group"] for r in rows])
    print(f"Device {DEVICE} | {len(rows)} images | {len(set(groups))} source receipts")
    print(f"Fractions {FRACTIONS} x {REPEATS} repeats x {N_FOLDS} folds\n", flush=True)

    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(splitter.split(rows, y, groups=groups))

    results = []
    for fraction in FRACTIONS:
        aucs, receipts_used, images_used = [], [], []

        for repeat in range(REPEATS):
            rng = np.random.default_rng(SEED + repeat)
            oof = np.zeros(len(rows))

            for train_idx, test_idx in folds:
                train_groups = np.unique(groups[train_idx])
                keep_count = max(int(round(len(train_groups) * fraction)), 4)
                keep = set(rng.choice(train_groups, keep_count, replace=False).tolist())
                sub_idx = np.array([i for i in train_idx if groups[i] in keep])

                # A fold with only one class left cannot train — skip this draw.
                if len(set(y[sub_idx].tolist())) < 2:
                    continue

                train_rows = [rows[i] for i in sub_idx]
                test_rows = [rows[i] for i in test_idx]
                oof[test_idx] = train_once(train_rows, test_rows)

                receipts_used.append(len(keep))
                images_used.append(len(sub_idx))

            aucs.append(roc_auc_score(y, oof))

        mean_auc = float(np.mean(aucs))
        results.append({
            "fraction": fraction,
            "train_receipts": int(np.mean(receipts_used)),
            "train_images": int(np.mean(images_used)),
            "pooled_auc": round(mean_auc, 4),
            "spread": round(float(np.std(aucs)), 4),
        })
        print(f"  fraction {fraction:.2f} -> {results[-1]['train_receipts']:3d} receipts "
              f"/ {results[-1]['train_images']:3d} images   pooled AUC {mean_auc:.4f}",
              flush=True)

    ASSETS.mkdir(parents=True, exist_ok=True)
    with open(ASSETS / "learning_curve.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 62)
    print("LEARNING CURVE")
    print("=" * 62)
    for row in results:
        print(f"  {row['train_receipts']:3d} receipts ({row['train_images']:3d} images)"
              f"   AUC {row['pooled_auc']:.4f}  +/- {row['spread']:.4f}")

    first, last = results[0]["pooled_auc"], results[-1]["pooled_auc"]
    late_gain = results[-1]["pooled_auc"] - results[-2]["pooled_auc"]
    print(f"\n  Total gain across the curve   : {last - first:+.4f}")
    print(f"  Gain over the final step      : {late_gain:+.4f}")
    print("\n  A still-rising final step means more receipts should raise AUC.")
    print("  A flat or negative final step means more of the same data will not.")
    print("\nSaved -> report/assets/learning_curve.csv")


if __name__ == "__main__":
    sys.exit(main())
