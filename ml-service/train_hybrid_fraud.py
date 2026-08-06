"""
Hybrid Fraud Classifier — CNN (MobileNetV2) features + structured image signals → XGBoost head.
Owner: Ranjeet Singh / Team ARAJ — Sprint 3.

WHY THIS SCRIPT EXISTS
----------------------
The previous Colab hybrid attempts trained on SYNTHETIC random-noise data because the real
receipt images were never mounted. This script FAILS LOUDLY if the real images are missing —
there is NO synthetic fallback. Reported AUCs are only valid when trained on the real 200 images.

Structured signals (no Gemini API needed — all computed locally with cv2/PIL):
  1. Blur score (Laplacian variance) — from ocr.py BLUR_THRESHOLD logic
  2. Writing-density anomaly (10 horizontal bands) — from ocr.py _detect_density_anomaly
  3. Basic image stats: brightness, contrast, entropy, aspect ratio

Combined feature vector per image:
  [MobileNetV2 1280-dim pooled features] + [blur] + [10 density bands] + [4 image stats]
  = 1295 features → XGBoost classifier

Usage (Colab, after uploading/mounting repo with real images in dataset/):
    !python ml-service/train_hybrid_fraud.py

Outputs:
    ml-service/models/hybrid_fraud_xgb.json           (XGBoost model)
    ml-service/models/hybrid_fraud_meta.json          (feature extractor config)
    report/assets/hybrid_fraud_results.csv            (AUC, per-class recall)
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── 1. REAL-IMAGE GUARD (NO SYNTHETIC FALLBACK) ──────────────────
def ensure_real_images():
    """Verify the real receipt images exist. Raised RuntimeError if < 200."""
    image_dirs = {
        "genuine": REPO_ROOT / "dataset" / "genuine",
        "tampered": REPO_ROOT / "dataset" / "tampered",
        "indian": REPO_ROOT / "dataset" / "indian",
    }
    total = 0
    for name, d in image_dirs.items():
        if not d.exists():
            print(f"[WARN] {name}/ folder missing: {d}")
            continue
        count = sum(1 for f in d.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"})
        print(f"  {name}/: {count} images")
        total += count

    if total < 200:
        raise RuntimeError(
            f"Only {total} real images found (< 200). The real receipt images are NOT in the repo "
            "(gitignored). Mount Google Drive and copy genuine/, tampered/, indian/ into dataset/ "
            "before running. NEVER train on synthetic data — results are invalid."
        )
    print(f"✅ {total} real images present. Proceeding with REAL data.")
    return total


# ── 2. STRUCTURED SIGNAL EXTRACTION (cv2/PIL only — no API) ─────
def extract_structured_signals(image_path):
    """
    Computes image-level fraud signals that ocr.py uses, WITHOUT calling Gemini.
    Returns dict: blur_score, density_bands[10], brightness, contrast, entropy, aspect_ratio.
    """
    import cv2

    signals = {
        "blur_score": 0.0,
        "density_bands": [0.0] * 10,
        "brightness": 0.0,
        "contrast": 0.0,
        "entropy": 0.0,
        "aspect_ratio": 1.0,
    }

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return signals

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Blur score (Laplacian variance)
        signals["blur_score"] = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 2. Density bands (10 horizontal) — mirrors ocr.py _detect_density_anomaly
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        h, w = thresh.shape
        band_h = max(1, h // 10)
        for i in range(10):
            band = thresh[i * band_h: (i + 1) * band_h, :]
            signals["density_bands"][i] = float(band.sum() / (band.size * 255))

        # 3. Brightness / contrast
        signals["brightness"] = float(gray.mean())
        signals["contrast"] = float(gray.std())

        # 4. Entropy
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist / max(hist.sum(), 1e-9)
        signals["entropy"] = float(-np.sum(hist * np.log2(hist + 1e-9)))

        # 5. Aspect ratio
        signals["aspect_ratio"] = float(h / max(w, 1))

    except Exception as e:
        print(f"[WARN] Signal extraction failed for {image_path}: {e}")

    return signals


# ── 3. CNN FEATURE EXTRACTION (MobileNetV2) ──────────────────────
def extract_cnn_features(image_paths, batch_size=16):
    """
    Extracts 1280-dim pooled features from MobileNetV2 for each image.
    Uses correct global average pooling (MobileNetV2 has no 'avgpool' attribute — the
    previous Colab attempt crashed on that). Returns np.ndarray (N, 1280).
    """
    import torch
    import torchvision.transforms as T
    from torchvision import models
    from PIL import Image

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Feature extractor device: {device}")

    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    # Strip the classifier head — keep features only. MobileNetV2's features output
    # is (N, 1280, 7, 7); we apply adaptive avg pool manually (correct approach).
    model = model.features.to(device)
    model.eval()

    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    all_features = []
    with torch.no_grad():
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            tensors = []
            for p in batch_paths:
                img = Image.open(p).convert("RGB")
                tensors.append(transform(img))
            batch = torch.stack(tensors).to(device)
            feats = model(batch)                   # (B, 1280, 7, 7)
            pooled = feats.mean(dim=[2, 3])        # (B, 1280) — correct GAP
            all_features.append(pooled.cpu().numpy())
            print(f"  Extracted {min(i + batch_size, len(image_paths))}/{len(image_paths)}")

    return np.vstack(all_features)


# ── 4. MAIN ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Train hybrid CNN+XGBoost fraud classifier on REAL data.")
    parser.add_argument("--epochs", type=int, default=5, help="CNN feature extraction pass (unused — features only)")
    parser.add_argument("--xgb-rounds", type=int, default=200, help="XGBoost boosting rounds")
    args = parser.parse_args()

    print("=" * 60)
    print("HYBRID FRAUD CLASSIFIER — REAL DATA ONLY")
    print("=" * 60)

    # Guard: real images MUST exist
    ensure_real_images()

    # CSV manifest (image_path, label)
    import pandas as pd
    manifest_path = REPO_ROOT / "dataset" / "processed" / "fraud_manifest.csv"
    if not manifest_path.exists():
        raise RuntimeError(f"Missing {manifest_path}")
    df = pd.read_csv(manifest_path)
    if "image_present" in df.columns:
        df = df[df["image_present"] == 1]
    print(f"Manifest rows: {len(df)}")

    # Resolve paths + collect labels
    rows = []
    for _, r in df.iterrows():
        p = Path(str(r["image_path"]))
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            label = 1 if str(r["label"]).strip() == "tampered" else 0
            rows.append((str(p), label))
    print(f"Resolved {len(rows)} real image paths with labels ({sum(l for _, l in rows)} tampered)")

    # Split train/val (80/20 stratified-ish)
    rng = np.random.RandomState(42)
    idx = rng.permutation(len(rows))
    n_val = max(1, int(len(rows) * 0.2))
    val_idx, train_idx = idx[:n_val], idx[n_val:]
    train_rows = [rows[i] for i in train_idx]
    val_rows = [rows[i] for i in val_idx]

    train_paths = [r[0] for r in train_rows]
    train_labels = np.array([r[1] for r in train_rows])
    val_paths = [r[0] for r in val_rows]
    val_labels = np.array([r[1] for r in val_rows])
    print(f"Train: {len(train_paths)} | Val: {len(val_paths)}")

    # CNN spatial features (real images)
    print("\n[1/3] Extracting MobileNetV2 spatial features (REAL images)...")
    cnn_train = extract_cnn_features(train_paths)
    cnn_val = extract_cnn_features(val_paths)

    # Structured signals (blur, density bands, brightness, etc.)
    print("\n[2/3] Extracting structured image signals (cv2)...")
    struct_train = [extract_structured_signals(p) for p in train_paths]
    struct_val = [extract_structured_signals(p) for p in val_paths]

    def make_feature_row(cnn_feat, signals):
        return np.concatenate([
            cnn_feat,
            [signals["blur_score"]],
            signals["density_bands"],
            [signals["brightness"], signals["contrast"], signals["entropy"], signals["aspect_ratio"]],
        ])

    X_train = np.array([make_feature_row(f, s) for f, s in zip(cnn_train, struct_train)])
    X_val = np.array([make_feature_row(f, s) for f, s in zip(cnn_val, struct_val)])
    print(f"Feature dim: {X_train.shape[1]} (1280 CNN + 15 structured)")

    # Train XGBoost
    print(f"\n[3/3] Training XGBoost head ({args.xgb_rounds} rounds)...")
    try:
        import xgboost as xgb
    except ImportError:
        print("ERROR: xgboost not installed. Run: pip install xgboost")
        sys.exit(1)

    clf = xgb.XGBClassifier(
        n_estimators=args.xgb_rounds,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="auc",
        early_stopping_rounds=20,
        random_state=42,
    )
    clf.fit(
        X_train, train_labels,
        eval_set=[(X_val, val_labels)],
        verbose=True,
    )

    # Evaluate
    from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
    val_probs = clf.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(val_labels, val_probs)
    val_preds = (val_probs >= 0.5).astype(int)

    print("\n" + "=" * 60)
    print(f"VALIDATION AUC (real data): {val_auc:.4f}")
    print("=" * 60)
    print("\nPer-class classification report:")
    print(classification_report(val_labels, val_preds, target_names=["genuine", "tampered"], digits=4))
    print("Confusion matrix:")
    print(confusion_matrix(val_labels, val_preds))

    # Save model + metadata
    model_dir = REPO_ROOT / "ml-service" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    clf.save_model(str(model_dir / "hybrid_fraud_xgb.json"))
    meta = {
        "feature_dim": int(X_train.shape[1]),
        "cnn_backbone": "mobilenet_v2",
        "structured_signals": ["blur_score", "density_bands_0..9", "brightness", "contrast", "entropy", "aspect_ratio"],
        "val_auc": round(float(val_auc), 4),
        "n_train": int(len(train_paths)),
        "n_val": int(len(val_paths)),
        "created": "Sprint 3 hybrid",
    }
    with open(model_dir / "hybrid_fraud_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nSaved → {model_dir / 'hybrid_fraud_xgb.json'}")
    print(f"Saved → {model_dir / 'hybrid_fraud_meta.json'}")

    # Write results CSV
    results_path = REPO_ROOT / "report" / "assets" / "hybrid_fraud_results.csv"
    report = classification_report(val_labels, val_preds, target_names=["genuine", "tampered"], output_dict=True)
    with open(results_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["val_auc", round(float(val_auc), 4)])
        writer.writerow(["genuine_recall", round(report["genuine"]["recall"], 4)])
        writer.writerow(["tampered_recall", round(report["tampered"]["recall"], 4)])
        writer.writerow(["genuine_precision", round(report["genuine"]["precision"], 4)])
        writer.writerow(["tampered_precision", round(report["tampered"]["precision"], 4)])
        writer.writerow(["accuracy", round(report["accuracy"], 4)])
    print(f"Saved → {results_path}")

    # Target check
    target = 0.90
    if val_auc >= target:
        print(f"\n✅ TARGET MET: AUC {val_auc:.4f} >= {target} — hybrid model is production-ready.")
    else:
        print(f"\n❌ TARGET NOT MET: AUC {val_auc:.4f} < {target} — more data/features needed.")


if __name__ == "__main__":
    main()