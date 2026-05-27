#!/usr/bin/env python3
"""
Day 7: starter fraud detector for receipt tampering risk.

Combines three signals into one fraud score (0.0-1.0):
1) Exact duplicate metadata check (merchant + date + total)
2) pHash near-duplicate image similarity
3) Handwritten-edit flag from labels CSV
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    # Package-style imports (when used as dataset.fraud_detector)
    from .exact_duplicate_check import duplicate_key
    from .perceptual_hash import compare_images
except ImportError:
    # Script-style imports (when run as python dataset/fraud_detector.py)
    from exact_duplicate_check import duplicate_key
    from perceptual_hash import compare_images


DEFAULT_RECEIPTS_CSV = "dataset/processed/receipts_master.csv"
DEFAULT_LABELS_CSV = "dataset/processed/labels.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute fraud score (0-1) from duplicate, pHash and handwritten signals."
    )
    parser.add_argument("--image", required=True, help="Path to current receipt image.")
    parser.add_argument("--merchant", required=True, help="Merchant name for current receipt.")
    parser.add_argument("--date", required=True, help="Receipt date (YYYY-MM-DD).")
    parser.add_argument("--total", required=True, help="Receipt total amount.")
    parser.add_argument(
        "--receipts-csv",
        default=DEFAULT_RECEIPTS_CSV,
        help=f"Receipt metadata CSV path (default: {DEFAULT_RECEIPTS_CSV}).",
    )
    parser.add_argument(
        "--labels-csv",
        default=DEFAULT_LABELS_CSV,
        help=f"Labels CSV path (default: {DEFAULT_LABELS_CSV}).",
    )
    parser.add_argument(
        "--reference-images",
        nargs="*",
        default=None,
        help="Optional explicit reference image paths for pHash comparison.",
    )
    parser.add_argument(
        "--reference-limit",
        type=int,
        default=150,
        help="Max images loaded from receipts CSV when --reference-images is not provided.",
    )
    parser.add_argument("--hash-size", type=int, default=8, help="pHash hash size. Default: 8.")
    parser.add_argument(
        "--phash-threshold",
        type=float,
        default=0.90,
        help="Similarity threshold where pHash starts adding fraud risk. Default: 0.90.",
    )
    parser.add_argument(
        "--normalize-merchant",
        action="store_true",
        help="Normalize merchant name for exact duplicate checks.",
    )
    parser.add_argument(
        "--merchant-field",
        default="merchant",
        help="Merchant column in receipts CSV.",
    )
    parser.add_argument("--date-field", default="date", help="Date column in receipts CSV.")
    parser.add_argument("--total-field", default="total", help="Total column in receipts CSV.")
    parser.add_argument(
        "--image-field",
        default="image_path",
        help="Image path column used in receipts/labels CSV.",
    )
    parser.add_argument("--label-field", default="label", help="Label column in labels CSV.")
    parser.add_argument("--notes-field", default="notes", help="Notes column in labels CSV.")
    parser.add_argument(
        "--weight-duplicate",
        type=float,
        default=0.50,
        help="Weight of exact duplicate signal.",
    )
    parser.add_argument(
        "--weight-phash",
        type=float,
        default=0.30,
        help="Weight of pHash similarity signal.",
    )
    parser.add_argument(
        "--weight-handwritten",
        type=float,
        default=0.20,
        help="Weight of handwritten flag signal.",
    )
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_reference_path(raw_path: str, root: Path) -> Path:
    candidate = Path(str(raw_path).strip()).expanduser()
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def exact_duplicate_matches(
    rows: list[dict],
    merchant: str,
    date: str,
    total: str | float,
    merchant_field: str,
    date_field: str,
    total_field: str,
    normalize_merchant_name: bool,
) -> list[dict]:
    input_row = {
        merchant_field: merchant,
        date_field: date,
        total_field: total,
    }
    target_key = duplicate_key(
        row=input_row,
        merchant_field=merchant_field,
        date_field=date_field,
        total_field=total_field,
        normalize_merchant_name=normalize_merchant_name,
    )

    matches = []
    for row in rows:
        row_key = duplicate_key(
            row=row,
            merchant_field=merchant_field,
            date_field=date_field,
            total_field=total_field,
            normalize_merchant_name=normalize_merchant_name,
        )
        if row_key == target_key:
            matches.append(row)
    return matches


def collect_reference_images(
    image_path: Path,
    root: Path,
    receipts_rows: list[dict],
    explicit_references: list[str] | None,
    image_field: str,
    reference_limit: int,
) -> list[Path]:
    refs: list[Path] = []
    seen: set[str] = set()
    current_abs = image_path.resolve()

    if explicit_references:
        raw_paths = explicit_references
    else:
        raw_paths = [str(row.get(image_field, "")).strip() for row in receipts_rows]

    for raw in raw_paths:
        if not raw:
            continue
        ref_path = to_reference_path(raw, root)
        if not ref_path.exists():
            continue
        ref_abs = ref_path.resolve()
        if ref_abs == current_abs:
            continue
        key = str(ref_abs)
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref_abs)
        if reference_limit > 0 and len(refs) >= reference_limit:
            break

    return refs


def best_phash_similarity(image_path: Path, reference_images: list[Path], hash_size: int) -> tuple[float, str | None]:
    if not reference_images:
        return 0.0, None

    best_score = 0.0
    best_reference: str | None = None

    for ref in reference_images:
        try:
            result = compare_images(image_a=image_path, image_b=ref, hash_size=hash_size)
        except Exception:
            continue
        score = float(result["similarity_score"])
        if score > best_score:
            best_score = score
            best_reference = str(ref)

    return best_score, best_reference


def has_handwritten_flag(
    labels_rows: list[dict],
    image_path: Path,
    root: Path,
    image_field: str,
    label_field: str,
    notes_field: str,
) -> bool:
    target_abs = image_path.resolve()
    try:
        target_rel = target_abs.relative_to(root).as_posix()
    except ValueError:
        target_rel = image_path.as_posix()
    target_name = image_path.name

    for row in labels_rows:
        raw_image = str(row.get(image_field, "")).strip()
        if not raw_image:
            continue

        row_path = to_reference_path(raw_image, root)
        row_rel = raw_image.replace("\\", "/").lstrip("./")

        same_image = False
        if row_path.exists():
            same_image = row_path.resolve() == target_abs
        if not same_image:
            same_image = row_rel == target_rel or row_rel.endswith(f"/{target_name}")
        if not same_image:
            continue

        label_value = str(row.get(label_field, "")).strip().lower()
        notes_value = str(row.get(notes_field, "")).strip().lower()
        if label_value == "handwritten_edit" or "handwritten" in notes_value:
            return True

    return False


def score_from_signals(
    exact_duplicate: bool,
    phash_similarity: float,
    handwritten_flag: bool,
    phash_threshold: float,
    weight_duplicate: float,
    weight_phash: float,
    weight_handwritten: float,
) -> dict:
    weights_total = weight_duplicate + weight_phash + weight_handwritten
    if weights_total <= 0:
        raise ValueError("Signal weights must sum to > 0.")

    # Normalize weights so custom input is always safe.
    dup_w = weight_duplicate / weights_total
    phash_w = weight_phash / weights_total
    hand_w = weight_handwritten / weights_total

    duplicate_component = 1.0 if exact_duplicate else 0.0
    handwritten_component = 1.0 if handwritten_flag else 0.0

    threshold = max(0.0, min(1.0, phash_threshold))
    similarity = max(0.0, min(1.0, phash_similarity))
    if threshold >= 1.0:
        phash_component = 0.0
    elif similarity <= threshold:
        phash_component = 0.0
    else:
        phash_component = (similarity - threshold) / (1.0 - threshold)

    fraud_score = (
        (dup_w * duplicate_component)
        + (phash_w * phash_component)
        + (hand_w * handwritten_component)
    )

    return {
        "fraud_score": round(max(0.0, min(1.0, fraud_score)), 4),
        "components": {
            "exact_duplicate_component": round(duplicate_component, 4),
            "phash_component": round(phash_component, 4),
            "handwritten_component": round(handwritten_component, 4),
        },
        "weights": {
            "exact_duplicate_weight": round(dup_w, 4),
            "phash_weight": round(phash_w, 4),
            "handwritten_weight": round(hand_w, 4),
        },
    }


def fraud_score(
    image_path: str | Path,
    merchant: str,
    date: str,
    total: str | float,
    receipts_csv: str | Path = DEFAULT_RECEIPTS_CSV,
    labels_csv: str | Path = DEFAULT_LABELS_CSV,
    reference_images: list[str] | None = None,
    hash_size: int = 8,
    phash_threshold: float = 0.90,
    normalize_merchant_name: bool = False,
    merchant_field: str = "merchant",
    date_field: str = "date",
    total_field: str = "total",
    image_field: str = "image_path",
    label_field: str = "label",
    notes_field: str = "notes",
    reference_limit: int = 150,
    weight_duplicate: float = 0.50,
    weight_phash: float = 0.30,
    weight_handwritten: float = 0.20,
) -> dict:
    root = project_root()
    image_abs = to_reference_path(str(image_path), root)
    if not image_abs.exists():
        raise FileNotFoundError(f"Input image not found: {image_abs}")

    receipts_path = to_reference_path(str(receipts_csv), root)
    labels_path = to_reference_path(str(labels_csv), root)

    receipts_rows = read_csv_rows(receipts_path)
    labels_rows = read_csv_rows(labels_path)

    matches = exact_duplicate_matches(
        rows=receipts_rows,
        merchant=merchant,
        date=date,
        total=total,
        merchant_field=merchant_field,
        date_field=date_field,
        total_field=total_field,
        normalize_merchant_name=normalize_merchant_name,
    )
    exact_duplicate = len(matches) > 0

    references = collect_reference_images(
        image_path=image_abs,
        root=root,
        receipts_rows=receipts_rows,
        explicit_references=reference_images,
        image_field=image_field,
        reference_limit=reference_limit,
    )
    phash_similarity, best_ref = best_phash_similarity(
        image_path=image_abs,
        reference_images=references,
        hash_size=hash_size,
    )
    handwritten_flag = has_handwritten_flag(
        labels_rows=labels_rows,
        image_path=image_abs,
        root=root,
        image_field=image_field,
        label_field=label_field,
        notes_field=notes_field,
    )

    scored = score_from_signals(
        exact_duplicate=exact_duplicate,
        phash_similarity=phash_similarity,
        handwritten_flag=handwritten_flag,
        phash_threshold=phash_threshold,
        weight_duplicate=weight_duplicate,
        weight_phash=weight_phash,
        weight_handwritten=weight_handwritten,
    )

    return {
        "fraud_score": scored["fraud_score"],
        "signals": {
            "exact_duplicate": exact_duplicate,
            "duplicate_match_count": len(matches),
            "phash_similarity": round(phash_similarity, 4),
            "phash_near_duplicate": phash_similarity >= phash_threshold,
            "handwritten_flag": handwritten_flag,
        },
        "details": {
            "best_reference_image": best_ref,
            "reference_images_checked": len(references),
            "duplicate_key": {
                merchant_field: merchant,
                date_field: date,
                total_field: str(total),
            },
            "components": scored["components"],
            "weights": scored["weights"],
        },
    }


def main() -> int:
    args = parse_args()
    result = fraud_score(
        image_path=args.image,
        merchant=args.merchant,
        date=args.date,
        total=args.total,
        receipts_csv=args.receipts_csv,
        labels_csv=args.labels_csv,
        reference_images=args.reference_images,
        hash_size=args.hash_size,
        phash_threshold=args.phash_threshold,
        normalize_merchant_name=args.normalize_merchant,
        merchant_field=args.merchant_field,
        date_field=args.date_field,
        total_field=args.total_field,
        image_field=args.image_field,
        label_field=args.label_field,
        notes_field=args.notes_field,
        reference_limit=args.reference_limit,
        weight_duplicate=args.weight_duplicate,
        weight_phash=args.weight_phash,
        weight_handwritten=args.weight_handwritten,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
