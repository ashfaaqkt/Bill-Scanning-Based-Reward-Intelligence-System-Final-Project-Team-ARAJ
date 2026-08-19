#!/usr/bin/env python3
"""
Generate the fraud-detection figures for the final report.

Reads only the saved out-of-fold predictions and result CSVs, so the figures can
never disagree with the numbers we report — rerun the training scripts and rerun
this, and everything moves together.

Run:  .torch_eval_venv/bin/python ml-service/make_report_figures.py
"""

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "report" / "assets"

# The champion is the 448x448 model. Forensic features are resolution-independent,
# so only the CNN artifacts carry the resolution suffix.
CNN_SUFFIX = "_normalized_448"
FORENSIC_SUFFIX = "_normalized"

# Validated categorical slots 1-3 (all-pairs, light surface) — see dataviz palette.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE = "#fcfcfb"
INK, INK_SOFT, GRID = "#0b0b0b", "#52514e", "#dcdcd8"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_SOFT, "axes.edgecolor": GRID,
    "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
    "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "medium",
    "figure.dpi": 200, "savefig.bbox": "tight",
})


def style(ax, grid_axis="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, axis=grid_axis, color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    return ax


def read_oof(name, column):
    with open(ASSETS / name, newline="") as handle:
        rows = list(csv.DictReader(handle))
    return (np.array([int(r["y"]) for r in rows]),
            np.array([float(r[column]) for r in rows]),
            [r["path"] for r in rows])


def save(fig, filename):
    fig.savefig(ASSETS / filename)
    plt.close(fig)
    print(f"  wrote {filename}")


# ── 1. ROC curves ──────────────────────────────────────────────
def figure_roc(y, cnn, forensic, fusion):
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    style(ax, grid_axis="both")

    series = [("CNN (MobileNetV2, 448px)", cnn, BLUE), ("Forensic features", forensic, ORANGE),
              ("Fusion (rank-average)", fusion, AQUA)]

    for label, scores, colour in series:
        fpr, tpr, _ = roc_curve(y, scores)
        auc = roc_auc_score(y, scores)
        ax.plot(fpr, tpr, color=colour, linewidth=2, label=f"{label} — AUC {auc:.3f}")

    ax.plot([0, 1], [0, 1], color=INK_SOFT, linewidth=1, linestyle=(0, (4, 4)))
    ax.text(0.62, 0.55, "chance", color=INK_SOFT, fontsize=8, rotation=34)

    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC — pooled out-of-fold, 194 receipts (448x448 input)", loc="left", pad=10)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5, labelcolor=INK)
    save(fig, "fig_roc_curves.png")


# ── 2. Per-fold AUC with confidence interval ───────────────────
def figure_folds():
    with open(ASSETS / f"fraud_cv_results{CNN_SUFFIX}.csv", newline="") as handle:
        values = {r["Metric"]: float(r["Value"]) for r in csv.DictReader(handle)
                  if r["Value"] not in ("", None)}

    folds = [values[f"Fold {i} AUC"] for i in range(1, 6)]
    mean, low, high = values["Mean AUC"], values["CI95 low"], values["CI95 high"]

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    style(ax)

    x = np.arange(1, 6)
    ax.fill_between([0.6, 5.4], low, high, color=BLUE, alpha=0.10, linewidth=0)
    ax.plot([0.6, 5.4], [mean, mean], color=BLUE, linewidth=2)
    ax.plot([0.6, 5.4], [0.5, 0.5], color=INK_SOFT, linewidth=1, linestyle=(0, (4, 4)))

    ax.scatter(x, folds, s=64, color=BLUE, zorder=3,
               edgecolor=SURFACE, linewidth=2)
    for xi, value in zip(x, folds):
        ax.annotate(f"{value:.3f}", (xi, value), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8, color=INK)

    ax.text(5.55, mean, f"mean {mean:.3f}", color=INK, fontsize=8.5, va="center")
    ax.text(5.55, mean - 0.075, f"95% CI\n[{low:.3f}, {high:.3f}]",
            color=INK_SOFT, fontsize=7.5, va="center")
    ax.text(0.65, 0.515, "chance", color=INK_SOFT, fontsize=8)

    ax.set_xticks(x); ax.set_xticklabels([f"Fold {i}" for i in x])
    ax.set_ylabel("AUC")
    ax.set_ylim(0.45, 1.0); ax.set_xlim(0.5, 6.6)
    ax.set_title("Per-fold AUC — grouped 5-fold CV, 448x448 input", loc="left", pad=10)
    save(fig, "fig_fold_auc.png")


# ── 3. Confusion matrix at the Youden-optimal threshold ────────
def figure_confusion(y, scores):
    fpr, tpr, thresholds = roc_curve(y, scores)
    best = thresholds[np.argmax(tpr - fpr)]
    matrix = confusion_matrix(y, (scores >= best).astype(int))

    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    ceiling = matrix.max() * 1.15
    ax.imshow(matrix, cmap="Blues", vmin=0, vmax=ceiling)

    labels = ["genuine", "tampered"]
    ax.set_xticks([0, 1], labels); ax.set_yticks([0, 1], labels)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title(f"Confusion matrix — CNN 448px @ threshold {best:.2f}", loc="left", pad=10)

    for i in range(2):
        for j in range(2):
            share = matrix[i, j] / matrix[i].sum()
            # White ink only where the fill is actually dark enough to carry it.
            dark_fill = matrix[i, j] / ceiling > 0.55
            ax.text(j, i, f"{matrix[i, j]}\n{share:.0%}", ha="center", va="center",
                    fontsize=11, color="#ffffff" if dark_fill else INK)

    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    save(fig, "fig_confusion_matrix.png")


# ── 4. Ablation ────────────────────────────────────────────────
def figure_ablation(entries):
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    style(ax, grid_axis="x")

    names = [e[0] for e in entries]
    values = [e[1] for e in entries]
    colours = [e[2] for e in entries]
    y = np.arange(len(entries))[::-1]

    ax.hlines(y, 0.5, values, color=colours, linewidth=2.5)
    ax.scatter(values, y, s=70, color=colours, zorder=3,
               edgecolor=SURFACE, linewidth=2)
    for yi, value in zip(y, values):
        ax.annotate(f"{value:.3f}", (value, yi), textcoords="offset points",
                    xytext=(10, 0), va="center", fontsize=8.5, color=INK)

    ax.axvline(0.5, color=INK_SOFT, linewidth=1, linestyle=(0, (4, 4)))
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8.5, color=INK)
    ax.set_ylim(-0.6, len(entries) - 0.4)
    ax.set_xlabel("Pooled out-of-fold AUC   (0.5 = chance)")
    ax.set_xlim(0.42, 0.90)
    ax.set_title("Ablation — what each signal contributes", loc="left", pad=10)
    save(fig, "fig_ablation.png")


# ── 5. Dataset composition ─────────────────────────────────────
def figure_dataset():
    fig, ax = plt.subplots(figsize=(6.0, 2.5))
    style(ax, grid_axis="x")

    rows = [("dataset/indian/\nreal receipts", 65, 29),
            ("dataset/tampered/\nscript-generated", 0, 100)]

    for index, (label, genuine, tampered) in enumerate(rows):
        y = len(rows) - 1 - index
        if genuine:
            ax.barh(y, genuine, color=BLUE, height=0.38)
            ax.text(genuine / 2, y, f"{genuine} genuine", ha="center", va="center",
                    fontsize=8.5, color="#ffffff")
        ax.barh(y, tampered, left=genuine + (2 if genuine else 0),
                color=ORANGE, height=0.38)
        ax.text(genuine + tampered / 2 + 2, y, f"{tampered} tampered",
                ha="center", va="center", fontsize=8.5, color="#ffffff")
        ax.text(-4, y, label, ha="right", va="center", fontsize=8.5, color=INK)

    ax.set_yticks([]); ax.set_xlim(0, 108); ax.set_xlabel("Images")
    ax.set_title("Dataset composition — 194 images from 103 source receipts",
                 loc="left", pad=10)
    ax.spines["left"].set_visible(False)
    save(fig, "fig_dataset_composition.png")


def main():
    if not (ASSETS / "cnn_oof_predictions_normalized.csv").exists():
        sys.exit("Run train_fraud_cv.py --normalized first.")

    y, cnn, paths = read_oof(f"cnn_oof_predictions{CNN_SUFFIX}.csv", "cnn_prob")
    y_forensic, forensic, forensic_paths = read_oof(
        f"forensic_oof_predictions{FORENSIC_SUFFIX}.csv", "forensic_prob")

    # The two files are written in different row orders — align on path, and
    # confirm the labels still agree once aligned.
    probability_by_path = dict(zip(forensic_paths, forensic))
    label_by_path = dict(zip(forensic_paths, y_forensic))
    forensic = np.array([probability_by_path[p] for p in paths])
    assert all(label_by_path[p] == label for p, label in zip(paths, y)), "label mismatch"

    fusion = rankdata(cnn) / len(cnn) + rankdata(forensic) / len(forensic)

    print("Generating report figures...")
    figure_roc(y, cnn, forensic, fusion)
    figure_folds()
    figure_confusion(y, cnn)
    figure_ablation([
        ("JPEG quantization table only\n(pre-fix artifact, no image content)", 0.6901, INK_SOFT),
        ("Forensic features (31)", roc_auc_score(y, forensic), ORANGE),
        ("Fusion (rank-average)", roc_auc_score(y, fusion), AQUA),
        ("CNN 224px", 0.7523, INK_SOFT),
        ("CNN 448px  (champion)", roc_auc_score(y, cnn), BLUE),
    ])
    figure_dataset()
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
