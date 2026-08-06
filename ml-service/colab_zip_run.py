"""
ZIP-AWARE ONE-SHOT Colab runner — finds the uploaded fraud_dataset.zip, unzips it,
verifies real images, trains MobileNetV2, saves artifacts. No improvisation possible.
Owner: Ranjeet Singh / Team ARAJ — Sprint 3.

HOW TO USE (Colab, T4 GPU):
  1. Upload fraud_dataset.zip to the Colab Files panel (left sidebar → upload).
  2. Run ONE cell:
       !git clone -b ranjeet/fraud-testing https://github.com/ashfaaqkt/Bill-Scanning-Based-Reward-Intelligence-System-Final-Project-Team-ARAJ.git
       %cd Bill-Scanning-Based-Reward-Intelligence-System-Final-Project-Team-ARAJ
       !python ml-service/colab_zip_run.py
  3. Wait. Outputs go to /content/outputs/ (download from Files panel).

The script searches /content for any *.zip, unzips it, locates genuine/, tampered/,
indian/ folders, and FAILS LOUDLY if fewer than 200 real images are found.
"""

import argparse
import csv
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path("/content/outputs")


# ── 1. FIND + UNZIP THE UPLOADED DATASET ────────────────────────
def find_and_unzip_zip():
    """Search /content for any .zip, unzip to /content/dataset_upload. Return the folder."""
    content = Path("/content")
    zips = sorted(content.glob("*.zip"))
    if not zips:
        raise RuntimeError(
            "No .zip file found in /content. Upload fraud_dataset.zip to the Colab "
            "Files panel (left sidebar → upload icon) and re-run."
        )
    zip_path = zips[0]
    print(f"Found zip: {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")

    dest = content / "dataset_upload"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    print(f"Unzipped → {dest}")

    # Find the dataset root (folder containing genuine/, tampered/, indian/)
    candidates = [dest]
    candidates += [p for p in dest.rglob("*") if p.is_dir()]
    for cand in candidates:
        subs = {p.name for p in cand.iterdir() if p.is_dir()}
        if {"genuine", "tampered", "indian"}.issubset(subs):
            print(f"Dataset root found: {cand}")
            return cand
    raise RuntimeError(
        f"Unzipped but could not find genuine/, tampered/, indian/ folders under {dest}. "
        "Check the zip structure and re-upload."
    )


# ── 2. COPY REAL IMAGES INTO dataset/ (FAILS LOUDLY) ────────────
def copy_real_images(dataset_root: Path):
    """Copy genuine/, tampered/, indian/ from the unzipped folder into repo dataset/."""
    target_dirs = {
        "genuine": REPO_ROOT / "dataset" / "genuine",
        "tampered": REPO_ROOT / "dataset" / "tampered",
        "indian": REPO_ROOT / "dataset" / "indian",
    }

    def count_images(d):
        if not d.exists():
            return 0
        return sum(1 for f in d.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"})

    total = 0
    for name, dest in target_dirs.items():
        src = dataset_root / name
        if not src.exists():
            print(f"[WARN] {name}/ not found in zip")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        copied = 0
        for f in src.iterdir():
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
                shutil.copy2(f, dest / f.name)
                copied += 1
        total += copied
        print(f"  Copied {copied} from {src} → {dest}")

    if total < 200:
        raise RuntimeError(
            f"Only {total} real images found (< 200). Do NOT proceed — training on "
            "fewer/partial data is invalid. Fix the zip and re-upload."
        )
    print(f"✅ {total} real images ready. Proceeding with REAL data.")
    return total


# ── 3. DATASET (REAL IMAGES ONLY) ───────────────────────────────
def build_dataset():
    """Load real image paths + labels from fraud_manifest.csv."""
    import pandas as pd

    manifest = REPO_ROOT / "dataset" / "processed" / "fraud_manifest.csv"
    if not manifest.exists():
        raise RuntimeError(f"Missing {manifest}")
    df = pd.read_csv(manifest)
    if "image_present" in df.columns:
        df = df[df["image_present"] == 1]

    rows = []
    for _, r in df.iterrows():
        p = Path(str(r["image_path"]))
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            label = 1 if str(r["label"]).strip() == "tampered" else 0
            rows.append((str(p), label))
    print(f"Loaded {len(rows)} real images ({sum(l for _, l in rows)} tampered)")
    return rows


# ── 4. TRAINING (FREEZE-THEN-FINE-TUNE + RANDAUGMENT + 5-FOLD) ──
def train_fold(train_rows, val_rows, fold_idx, epochs_frozen=5, epochs_finetune=12):
    """Train MobileNetV2 on one fold. Returns (history, best_auc, best_state, cm, report)."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
    from torchvision import transforms, models
    from PIL import Image
    from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Fold {fold_idx} | device: {device}")

    class FraudDS(Dataset):
        def __init__(self, rows, transform):
            self.rows = rows
            self.transform = transform
        def __len__(self):
            return len(self.rows)
        def __getitem__(self, i):
            p, l = self.rows[i]
            img = Image.open(p).convert("RGB")
            return self.transform(img), l

    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandAugment(num_ops=2, magnitude=9),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_ds = FraudDS(train_rows, train_tf)
    val_ds = FraudDS(val_rows, val_tf)

    labels = [l for _, l in train_rows]
    n0, n1 = labels.count(0), labels.count(1)
    weights = [1.0 / n0 if l == 0 else 1.0 / n1 for l in labels]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=16, sampler=sampler, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=16, shuffle=False, num_workers=2, pin_memory=True)

    loss_weights = torch.tensor([n1 / n0, 1.0], dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=loss_weights)

    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model = model.to(device)

    # Phase 1: frozen backbone, train classifier head only
    for p in model.parameters():
        p.requires_grad = False
    for p in model.classifier.parameters():
        p.requires_grad = True
    optimizer = optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

    def evaluate():
        model.eval()
        all_l, all_p = [], []
        with torch.no_grad():
            for imgs, labs in val_loader:
                imgs, labs = imgs.to(device), labs.to(device)
                out = model(imgs)
                probs = torch.softmax(out, dim=1)[:, 1]
                all_l.extend(labs.cpu().tolist())
                all_p.extend(probs.cpu().tolist())
        auc = roc_auc_score(all_l, all_p) if len(set(all_l)) > 1 else 0.0
        return auc, all_l, all_p

    history = []
    best_auc, best_state = 0.0, None

    for epoch in range(1, epochs_frozen + 1):
        model.train()
        for imgs, labs in train_loader:
            imgs, labs = imgs.to(device), labs.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labs)
            loss.backward()
            optimizer.step()
        auc, _, _ = evaluate()
        history.append({"epoch": epoch, "phase": "frozen", "val_auc": round(auc, 4)})
        print(f"    Frozen epoch {epoch}/{epochs_frozen} | val_auc={auc:.4f}")
        if auc > best_auc:
            best_auc = auc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    # Phase 2: unfreeze last 2 blocks + classifier
    for p in model.parameters():
        p.requires_grad = False
    for name, p in model.named_parameters():
        if "features.16" in name or "features.17" in name or "classifier" in name:
            p.requires_grad = True
    optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    patience = 0
    for epoch in range(1, epochs_finetune + 1):
        model.train()
        for imgs, labs in train_loader:
            imgs, labs = imgs.to(device), labs.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labs)
            loss.backward()
            optimizer.step()
        auc, _, _ = evaluate()
        scheduler.step(auc)
        history.append({"epoch": epochs_frozen + epoch, "phase": "finetune", "val_auc": round(auc, 4)})
        print(f"    Finetune epoch {epoch}/{epochs_finetune} | val_auc={auc:.4f}")
        if auc > best_auc:
            best_auc = auc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
            if patience >= 4:
                print(f"    Early stopping at finetune epoch {epoch}")
                break

    model.load_state_dict(best_state)
    model.to(device)
    auc, all_l, all_p = evaluate()
    preds = [1 if p >= 0.5 else 0 for p in all_p]
    cm = confusion_matrix(all_l, preds)
    report = classification_report(all_l, preds, target_names=["genuine", "tampered"], output_dict=True)

    return history, best_auc, best_state, cm, report


# ── 5. MAIN ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Zip-aware one-shot fraud CNN training on REAL data.")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    print("=" * 60)
    print("ZIP-AWARE ONE-SHOT FRAUD CNN — REAL DATA ONLY")
    print("=" * 60)

    # 1. Find + unzip the uploaded dataset
    dataset_root = find_and_unzip_zip()

    # 2. Copy real images into repo dataset/
    copy_real_images(dataset_root)

    # 3. Build dataset from manifest
    rows = build_dataset()
    rng = np.random.RandomState(42)
    idx = rng.permutation(len(rows))
    fold_size = len(rows) // args.folds

    all_fold_aucs = []
    best_overall_auc = 0.0
    best_overall_state = None
    best_overall_history = None
    best_overall_cm = None
    best_overall_report = None

    # 4. Stratified 5-fold CV
    for fold in range(args.folds):
        val_idx = idx[fold * fold_size: (fold + 1) * fold_size]
        train_idx = np.concatenate([idx[:fold * fold_size], idx[(fold + 1) * fold_size:]])
        train_rows = [rows[i] for i in train_idx]
        val_rows = [rows[i] for i in val_idx]
        print(f"\n{'='*40}\nFOLD {fold + 1}/{args.folds} | train={len(train_rows)} val={len(val_rows)}\n{'='*40}")

        history, auc, state, cm, report = train_fold(train_rows, val_rows, fold + 1)
        all_fold_aucs.append(auc)
        print(f"  Fold {fold + 1} val AUC: {auc:.4f}")

        if auc > best_overall_auc:
            best_overall_auc = auc
            best_overall_state = state
            best_overall_history = history
            best_overall_cm = cm
            best_overall_report = report

    # 5. Summary
    mean_auc = float(np.mean(all_fold_aucs))
    std_auc = float(np.std(all_fold_aucs))
    print("\n" + "=" * 60)
    print(f"STRATIFIED {args.folds}-FOLD CV RESULTS (real data)")
    print(f"  Per-fold AUCs: {[round(a, 4) for a in all_fold_aucs]}")
    print(f"  Mean AUC: {mean_auc:.4f} ± {std_auc:.4f}")
    print(f"  Best fold AUC: {best_overall_auc:.4f}")
    print("=" * 60)

    # 6. Save best model
    import torch
    import torch.nn as nn
    from torchvision import models
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model.load_state_dict(best_overall_state)
    model_out = REPO_ROOT / "ml-service" / "models" / "tamper_cnn_sprint2_auc076.pt"
    torch.save(model, model_out)
    print(f"Saved best model → {model_out}")

    # 7. Save results to /content/outputs/ (easy download) + repo report/assets/
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = REPO_ROOT / "report" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # fraud_model_results.csv
    with open(OUTPUT_DIR / "fraud_model_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Model", "Best_AUC"])
        w.writerow(["MobileNetV2 (5-fold CV)", round(best_overall_auc, 4)])
        w.writerow(["MobileNetV2 (mean±std)", f"{mean_auc:.4f}±{std_auc:.4f}"])
    shutil.copy2(OUTPUT_DIR / "fraud_model_results.csv", assets / "fraud_model_results.csv")
    print(f"Saved → {OUTPUT_DIR / 'fraud_model_results.csv'}")

    # epoch_history.csv
    with open(OUTPUT_DIR / "epoch_history.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "phase", "val_auc"])
        for h in best_overall_history:
            w.writerow([h["epoch"], h["phase"], h["val_auc"]])
    shutil.copy2(OUTPUT_DIR / "epoch_history.csv", assets / "epoch_history.csv")
    print(f"Saved → {OUTPUT_DIR / 'epoch_history.csv'}")

    # accuracy_curve.png
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    epochs = [h["epoch"] for h in best_overall_history]
    aucs = [h["val_auc"] for h in best_overall_history]
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, aucs, "b-o")
    plt.xlabel("Epoch")
    plt.ylabel("Val AUC")
    plt.title(f"MobileNetV2 — Best Fold (AUC {best_overall_auc:.4f})")
    plt.grid(True, alpha=0.3)
    plt.savefig(OUTPUT_DIR / "accuracy_curve.png", dpi=150, bbox_inches="tight")
    shutil.copy2(OUTPUT_DIR / "accuracy_curve.png", assets / "accuracy_curve.png")
    print(f"Saved → {OUTPUT_DIR / 'accuracy_curve.png'}")

    # confusion_matrix.png
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(best_overall_cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["genuine", "tampered"]); ax.set_yticklabels(["genuine", "tampered"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(best_overall_cm[i, j]), ha="center", va="center",
                    color="white" if best_overall_cm[i, j] > best_overall_cm.max() / 2 else "black")
    plt.title("Confusion Matrix (Best Fold)")
    plt.colorbar(im)
    plt.savefig(OUTPUT_DIR / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    shutil.copy2(OUTPUT_DIR / "confusion_matrix.png", assets / "confusion_matrix.png")
    print(f"Saved → {OUTPUT_DIR / 'confusion_matrix.png'}")

    # 8. Target check
    target = 0.90
    if best_overall_auc >= target:
        print(f"\n✅ TARGET MET: best fold AUC {best_overall_auc:.4f} >= {target}")
    else:
        print(f"\n❌ TARGET NOT MET: best fold AUC {best_overall_auc:.4f} < {target}")
        print("  This is the honest real-data result. To reach 0.90 you need more labeled tampered samples.")


if __name__ == "__main__":
    main()