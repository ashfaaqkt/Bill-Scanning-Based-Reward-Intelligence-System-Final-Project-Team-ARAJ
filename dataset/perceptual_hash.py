#!/usr/bin/env python3
"""
Compute perceptual hash (pHash) similarity between two receipt images.

Example:
    python dataset/perceptual_hash.py \
      --image-a dataset/indian/jyoti_50_raw/Receipt\ 1.jpg \
      --image-b dataset/tampered/Receipt\ 1_tampered.jpg
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
import imagehash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two receipt images using perceptual hash (pHash)."
    )
    parser.add_argument("--image-a", required=True, help="Path to first image.")
    parser.add_argument("--image-b", required=True, help="Path to second image.")
    parser.add_argument(
        "--hash-size",
        type=int,
        default=8,
        help="pHash size. Default=8 (64-bit hash).",
    )
    return parser.parse_args()


def load_phash(image_path: Path, hash_size: int = 8) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img, hash_size=hash_size)


def similarity_score(hash_a: imagehash.ImageHash, hash_b: imagehash.ImageHash) -> tuple[int, float]:
    hamming_distance = hash_a - hash_b
    bit_length = hash_a.hash.size
    similarity = 1.0 - (hamming_distance / bit_length)
    return hamming_distance, similarity


def compare_images(image_a: Path, image_b: Path, hash_size: int = 8) -> dict:
    hash_a = load_phash(image_a, hash_size=hash_size)
    hash_b = load_phash(image_b, hash_size=hash_size)
    hamming_distance, similarity = similarity_score(hash_a, hash_b)
    return {
        "image_a": str(image_a),
        "image_b": str(image_b),
        "phash_a": str(hash_a),
        "phash_b": str(hash_b),
        "hamming_distance": hamming_distance,
        "similarity_score": round(similarity, 4),
    }


def main() -> int:
    args = parse_args()
    image_a = Path(args.image_a).expanduser().resolve()
    image_b = Path(args.image_b).expanduser().resolve()

    if not image_a.exists():
        raise FileNotFoundError(f"image-a not found: {image_a}")
    if not image_b.exists():
        raise FileNotFoundError(f"image-b not found: {image_b}")

    result = compare_images(image_a=image_a, image_b=image_b, hash_size=args.hash_size)
    print(f"image_a: {result['image_a']}")
    print(f"image_b: {result['image_b']}")
    print(f"phash_a: {result['phash_a']}")
    print(f"phash_b: {result['phash_b']}")
    print(f"hamming_distance: {result['hamming_distance']}")
    print(f"similarity_score: {result['similarity_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
