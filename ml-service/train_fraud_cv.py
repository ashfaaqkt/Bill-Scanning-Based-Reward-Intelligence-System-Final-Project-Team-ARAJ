#!/usr/bin/env python3
"""
Fraud CNN — 5-fold stratified cross-validation.

Replaces the single 39-image validation split used in Sprint 2. At n=39 the
confidence interval on AUC is roughly +/- 0.14, which is too wide to defend.
Cross-validation evaluates every one of the 194 labelled receipts exactly once
as a held-out sample and reports mean AUC with a confidence interval.

Also reports a source-confound control: genuine receipts all come from
dataset/indian/ while 80% of tampered come from dataset/tampered/, so a model
could separate the classes on camera/lighting rather than on tampering. The
control AUC is computed on dataset/indian/ receipts only, where both classes
share a source.

Run:  .torch_eval_venv/bin/python ml-service/train_fraud_cv.py
"""

import csv
import random
import re
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / "dataset" / "processed"
MODEL_OUT = REPO_ROOT / "ml-service" / "models" / "tamper_cnn_cv.pt"
MODEL_OUT_NORM = REPO_ROOT / "ml-service" / "models" / "tamper_cnn_cv_normalized.pt"
ASSETS = REPO_ROOT / "report" / "assets"

SEED = 42
N_FOLDS = 5
IMG_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 15
FREEZE_EPOCHS = 3       # train the head first, then fine-tune the whole backbone
PATIENCE = 5
LR_HEAD = 1e-3
LR_FINETUNE = 1e-4
WEIGHT_DECAY = 1e-4

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
elif torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")


# ── DATA ───────────────────────────────────────────────────────
def source_receipt(image_path):
    """
    Group key: the original receipt an image came from.

    generate_tampered.py derives 'Receipt 10_tampered.jpg' and
    'Receipt 10_tampered_v2.jpg' from 'Receipt 10.jpg'. All three are the same
    physical receipt, so they must never be split across train and test — the
    model would recognise the receipt instead of the tampering.
    """
    stem = Path(image_path).stem
    return re.sub(r"_tampered(_v\d+)?$", "", stem).strip().lower()


def load_rows(normalized=False):
    """
    Pools the existing train/val CSVs — CV makes its own splits.

    normalized=True reads dataset/processed/fraud_normalized.csv instead, where
    every image has been re-encoded through one identical JPEG path so the
    quantization table cannot leak the label. See dataset/normalize_images.py.
    """
    if normalized:
        with open(PROCESSED / "fraud_normalized.csv", newline="") as handle:
            return [{
                "path": str(REPO_ROOT / row["image_path"]),
                "y": 1 if row["label"] == "tampered" else 0,
                "source": row["source_folder"],
                "group": source_receipt(row["image_path"]),
            } for row in csv.DictReader(handle)]

    rows = []
    for name in ("fraud_train.csv", "fraud_val.csv"):
        with open(PROCESSED / name, newline="") as handle:
            for row in csv.DictReader(handle):
                label = str(row["label"]).strip()
                if label not in ("genuine", "tampered"):
                    continue  # multi_bill / handwritten are not part of the binary task
                path = REPO_ROOT / row["image_path"]
                if not path.exists():
                    continue
                rows.append({
                    "path": str(path),
                    "y": 1 if label == "tampered" else 0,
                    "source": row["image_path"].split("/")[1],
                    "group": source_receipt(row["image_path"]),
                })
    return rows


USE_NORMALIZED = "--normalized" in sys.argv


# Modest augmentation only — aggressive transforms destroy the very artifacts
# (edge seams, compression discontinuities) the model needs to detect.
TRAIN_TF = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomAffine(degrees=4, translate=(0.03, 0.03), scale=(0.95, 1.05)),
    transforms.ColorJitter(brightness=0.15, contrast=0.15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

EVAL_TF = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class ReceiptDataset(Dataset):
    def __init__(self, rows, transform):
        self.rows = rows
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(row["path"]) as img:
            tensor = self.transform(img.convert("RGB"))
        return tensor, row["y"]


# ── MODEL ──────────────────────────────────────────────────────
def build_model():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    return model.to(DEVICE)


def set_backbone_frozen(model, frozen):
    for param in model.features.parameters():
        param.requires_grad = not frozen


def predict(model, loader):
    """Returns (labels, probability-of-tampered)."""
    model.eval()
    labels, probs = [], []
    with torch.no_grad():
        for images, batch_labels in loader:
            outputs = model(images.to(DEVICE))
            batch_probs = torch.softmax(outputs, dim=1)[:, 1]
            probs.extend(batch_probs.cpu().numpy().tolist())
            labels.extend(batch_labels.numpy().tolist())
    return np.array(labels), np.array(probs)


def run_fold(fold, train_rows, val_rows, history_writer):
    train_loader = DataLoader(ReceiptDataset(train_rows, TRAIN_TF),
                              batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(ReceiptDataset(val_rows, EVAL_TF), batch_size=BATCH_SIZE)

    model = build_model()
    set_backbone_frozen(model, True)

    counts = np.bincount([r["y"] for r in train_rows], minlength=2)
    weights = torch.tensor(counts.sum() / (2.0 * np.maximum(counts, 1)),
                           dtype=torch.float32, device=DEVICE)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                            lr=LR_HEAD, weight_decay=WEIGHT_DECAY)

    best_auc, best_epoch, best_state, stale = 0.0, -1, None, 0

    for epoch in range(1, EPOCHS + 1):
        if epoch == FREEZE_EPOCHS + 1:
            set_backbone_frozen(model, False)
            optimizer = optim.AdamW(model.parameters(), lr=LR_FINETUNE,
                                    weight_decay=WEIGHT_DECAY)

        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        train_loss = running_loss / len(train_rows)
        val_labels, val_probs = predict(model, val_loader)
        val_auc = roc_auc_score(val_labels, val_probs)

        history_writer.writerow({
            "fold": fold, "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_auc": round(float(val_auc), 4),
            "phase": "head" if epoch <= FREEZE_EPOCHS else "finetune",
        })
        print(f"  fold {fold} epoch {epoch:2d}  loss {train_loss:.4f}  val_auc {val_auc:.4f}")

        if val_auc > best_auc:
            best_auc, best_epoch = float(val_auc), epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= PATIENCE:
                print(f"  fold {fold}: early stop at epoch {epoch}")
                break

    model.load_state_dict(best_state)
    val_labels, val_probs = predict(model, val_loader)
    return best_auc, best_epoch, model, val_labels, val_probs


def main():
    rows = load_rows(USE_NORMALIZED)
    labels = np.array([r["y"] for r in rows])
    groups = np.array([r["group"] for r in rows])
    print(f"Device: {DEVICE}")
    print(f"Pooled dataset: {len(rows)} images "
          f"({int((labels == 0).sum())} genuine / {int((labels == 1).sum())} tampered)")
    print(f"Grouped into {len(set(groups))} unique source receipts — "
          f"no receipt appears in both train and test\n")

    ASSETS.mkdir(parents=True, exist_ok=True)
    suffix = "_normalized" if USE_NORMALIZED else ""
    history_path = ASSETS / f"cv_fold_history{suffix}.csv"

    fold_aucs, best_overall, best_model = [], -1.0, None
    oof_labels, oof_probs, oof_sources, oof_rows = [], [], [], []

    with open(history_path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fold", "epoch", "train_loss",
                                                    "val_auc", "phase"])
        writer.writeheader()

        splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
        for fold, (train_idx, val_idx) in enumerate(
                splitter.split(rows, labels, groups=groups), start=1):
            train_rows = [rows[i] for i in train_idx]
            val_rows = [rows[i] for i in val_idx]

            leaked = set(groups[train_idx]) & set(groups[val_idx])
            assert not leaked, f"fold {fold} leaked source receipts: {leaked}"

            val_pct = 100 * len(val_rows) / len(rows)
            print(f"Fold {fold}/{N_FOLDS} — train {len(train_rows)} "
                  f"({100 - val_pct:.1f}%) / test {len(val_rows)} ({val_pct:.1f}%)")

            auc, epoch, model, val_labels, val_probs = run_fold(
                fold, train_rows, val_rows, writer)
            fold_aucs.append(auc)
            print(f"  fold {fold} best AUC {auc:.4f} @ epoch {epoch}\n")

            oof_labels.extend(val_labels.tolist())
            oof_probs.extend(val_probs.tolist())
            oof_sources.extend(r["source"] for r in val_rows)
            oof_rows.extend(val_rows)

            if auc > best_overall:
                best_overall, best_model = auc, model

    aucs = np.array(fold_aucs)
    mean_auc, std_auc = float(aucs.mean()), float(aucs.std(ddof=1))
    half_width = 1.96 * std_auc / np.sqrt(N_FOLDS)   # 95% CI on the mean

    oof_labels = np.array(oof_labels)
    oof_probs = np.array(oof_probs)
    oof_auc = float(roc_auc_score(oof_labels, oof_probs))

    # Source-confound control: indian/ only, where both classes share a source.
    mask = np.array([s == "indian" for s in oof_sources])
    control_auc = None
    if mask.sum() and len(set(oof_labels[mask].tolist())) == 2:
        control_auc = float(roc_auc_score(oof_labels[mask], oof_probs[mask]))

    print("=" * 62)
    print("5-FOLD CROSS-VALIDATION RESULT")
    print("=" * 62)
    for i, auc in enumerate(fold_aucs, start=1):
        print(f"  fold {i}: AUC {auc:.4f}")
    print(f"\n  Mean AUC        : {mean_auc:.4f} +/- {std_auc:.4f} (SD)")
    print(f"  95% CI (mean)   : [{mean_auc - half_width:.4f}, {mean_auc + half_width:.4f}]")
    print(f"  Pooled OOF AUC  : {oof_auc:.4f}   (all {len(oof_labels)} receipts, each held out once)")
    if control_auc is not None:
        print(f"  Source control  : {control_auc:.4f}   (indian/ only, n={int(mask.sum())} "
              f"— guards against learning the folder, not the tampering)")
    print(f"\n  Reference points:")
    print(f"    Sprint 2, single 39-image split          : 0.76 (unverified)")
    print(f"    Ungrouped 5-fold CV (leaked source recs) : 0.78 (inflated)")

    out_path = MODEL_OUT_NORM if USE_NORMALIZED else MODEL_OUT
    torch.save(best_model, out_path)   # full nn.Module — fraud.py loads this directly
    print(f"\nSaved best-fold model → {out_path.name} "
          f"({out_path.stat().st_size / 1e6:.1f} MB)")

    with open(ASSETS / f"fraud_cv_results{suffix}.csv", "w", newline="") as handle:
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
            writer.writerow(["Source-control AUC (indian only)", round(control_auc, 4)])
        writer.writerow(["N receipts", len(rows)])
        writer.writerow(["Folds", N_FOLDS])

    with open(ASSETS / f"cnn_oof_predictions{suffix}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "group", "y", "cnn_prob"])
        for row, probability in zip(oof_rows, oof_probs):
            writer.writerow([row["path"], row["group"], row["y"], round(float(probability), 6)])

    print(f"Saved → fraud_cv_results{suffix}.csv, cv_fold_history{suffix}.csv, "
          f"cnn_oof_predictions{suffix}.csv")


if __name__ == "__main__":
    sys.exit(main())
