#!/usr/bin/env python3
"""
Generate tampered receipt images by adding handwritten-style overlays.

Example:
    python dataset/generate_tampered.py \
      --input dataset/genuine \
      --output-dir dataset/tampered \
      --count 1
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    "/System/Library/Fonts/Supplemental/Noteworthy.ttc",
    "/Library/Fonts/Arial.ttf",
]
OVERLAY_PHRASES = [
    "Paid cash",
    "Bill corrected",
    "Revised total",
    "Round off adj",
    "Approved",
    "Recheck",
    "Manual edit",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create handwritten-overlay tampered versions of receipt images."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input receipt image path or directory containing receipt images.",
    )
    parser.add_argument(
        "--output-dir",
        default="dataset/tampered",
        help="Directory where generated tampered images are written.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of tampered variants to generate per input image.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Process only the first N images when input is a directory (0 means all).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    return parser.parse_args()


def load_font(size: int) -> ImageFont.ImageFont:
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def discover_images(input_path: Path, max_images: int) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    images = [
        p
        for p in sorted(input_path.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if max_images > 0:
        return images[:max_images]
    return images


def random_amount(rng: random.Random) -> str:
    value = rng.randint(10, 499) + rng.choice([0.0, 0.5, 0.99])
    prefix = rng.choice(["+", "-", "Rs", "₹"])
    if prefix in {"Rs", "₹"}:
        return f"{prefix} {value:.2f}"
    return f"{prefix}{value:.2f}"


def build_overlay_lines(rng: random.Random) -> list[str]:
    lines = [rng.choice(OVERLAY_PHRASES)]
    if rng.random() > 0.5:
        lines.append(random_amount(rng))
    if rng.random() > 0.65:
        lines.append(datetime.now().strftime("%d/%m"))
    return lines


def draw_handwritten_overlay(image: Image.Image, rng: random.Random) -> Image.Image:
    base = image.convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))

    lines = build_overlay_lines(rng)
    y_cursor = int(height * rng.uniform(0.12, 0.72))
    x_base = int(width * rng.uniform(0.45, 0.78))

    for line in lines:
        font_size = max(14, int(min(width, height) * rng.uniform(0.03, 0.06)))
        font = load_font(font_size)
        color = (
            rng.randint(10, 60),
            rng.randint(10, 60),
            rng.randint(10, 60),
            rng.randint(120, 220),
        )
        pad = 20
        scratch = Image.new("RGBA", (max(120, int(width * 0.45)), font_size + pad), (0, 0, 0, 0))
        draw = ImageDraw.Draw(scratch)

        # Draw text multiple times with slight jitter for a rough handwritten look.
        for _ in range(rng.randint(2, 3)):
            jitter_x = rng.randint(-1, 1)
            jitter_y = rng.randint(-1, 1)
            draw.text((10 + jitter_x, 5 + jitter_y), line, font=font, fill=color)

        rotated = scratch.rotate(rng.uniform(-11, 11), expand=True, resample=Image.Resampling.BICUBIC)
        x = max(0, min(width - rotated.width, x_base + rng.randint(-35, 20)))
        y = max(0, min(height - rotated.height, y_cursor + rng.randint(-8, 10)))
        overlay.alpha_composite(rotated, dest=(x, y))
        y_cursor += int(font_size * rng.uniform(1.3, 1.8))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    return combined


def output_path_for(input_file: Path, output_dir: Path, variant: int, count: int) -> Path:
    suffix = input_file.suffix.lower() if input_file.suffix else ".jpg"
    if count == 1:
        name = f"{input_file.stem}_tampered{suffix}"
    else:
        name = f"{input_file.stem}_tampered_{variant:02d}{suffix}"
    return output_dir / name


def run(input_path: Path, output_dir: Path, count: int, max_images: int, seed: int | None) -> int:
    rng = random.Random(seed)
    images = discover_images(input_path, max_images=max_images)
    if not images:
        print(f"[WARN] No images found in: {input_path}")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for image_path in images:
        with Image.open(image_path) as img:
            for i in range(1, count + 1):
                tampered = draw_handwritten_overlay(img, rng)
                out_file = output_path_for(image_path, output_dir, i, count)
                tampered.save(out_file, quality=95)
                print(f"[OK] {image_path} -> {out_file}")
                generated += 1

    print(f"[DONE] Generated {generated} tampered image(s).")
    return generated


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if args.count < 1:
        raise ValueError("--count must be >= 1")
    if args.max_images < 0:
        raise ValueError("--max-images must be >= 0")

    run(
        input_path=input_path,
        output_dir=output_dir,
        count=args.count,
        max_images=args.max_images,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
