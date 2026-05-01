#!/usr/bin/env python3
"""
Generate tampered receipt images with multiple tamper styles.

Example:
    python dataset/generate_tampered.py \
      --input dataset/genuine \
      --output-dir dataset/tampered \
      --count 1 \
      --modes brightness,duplicate_copy,number_overwrite
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


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
TAMPER_MODES = ("brightness", "duplicate_copy", "number_overwrite", "handwritten")


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
    parser.add_argument(
        "--modes",
        default="brightness,duplicate_copy,number_overwrite",
        help=(
            "Comma-separated tamper modes. "
            "Supported: brightness, duplicate_copy, number_overwrite, handwritten."
        ),
    )
    parser.add_argument(
        "--name-suffix",
        default="tampered",
        help=(
            "Output filename suffix. Example: "
            "Receipt 1_<name-suffix>.jpg"
        ),
    )
    return parser.parse_args()


def parse_modes(mode_text: str) -> list[str]:
    modes = [m.strip().lower() for m in mode_text.split(",") if m.strip()]
    if not modes:
        raise ValueError("At least one tamper mode is required in --modes")
    invalid = [m for m in modes if m not in TAMPER_MODES]
    if invalid:
        supported = ", ".join(TAMPER_MODES)
        raise ValueError(f"Unsupported mode(s): {', '.join(invalid)}. Supported: {supported}")
    return modes


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


def apply_brightness_tamper(image: Image.Image, rng: random.Random) -> Image.Image:
    base = image.convert("RGB")
    if rng.random() < 0.5:
        factor = rng.uniform(0.58, 0.85)  # darker
    else:
        factor = rng.uniform(1.18, 1.42)  # brighter
    return ImageEnhance.Brightness(base).enhance(factor)


def apply_duplicate_copy_tamper(image: Image.Image, rng: random.Random) -> Image.Image:
    base = image.convert("RGB").copy()
    width, height = base.size

    min_patch = max(40, int(min(width, height) * 0.08))
    max_patch_w = max(min_patch + 1, int(width * 0.25))
    max_patch_h = max(min_patch + 1, int(height * 0.12))
    patch_w = rng.randint(min_patch, max_patch_w)
    patch_h = rng.randint(min_patch, max_patch_h)

    src_x = rng.randint(0, max(0, width - patch_w))
    src_y = rng.randint(0, max(0, height - patch_h))
    patch = base.crop((src_x, src_y, src_x + patch_w, src_y + patch_h))

    dst_x = rng.randint(0, max(0, width - patch_w))
    dst_y = rng.randint(int(height * 0.35), max(int(height * 0.35), height - patch_h))
    base.paste(patch, (dst_x, dst_y))
    return base


def apply_number_overwrite_tamper(image: Image.Image, rng: random.Random) -> Image.Image:
    base = image.convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    old_val = f"{rng.randint(120, 980)}.{rng.choice(['00', '50', '99'])}"
    delta = rng.randint(15, 180)
    if rng.random() < 0.5:
        new_num = max(20, int(float(old_val)) - delta)
    else:
        new_num = int(float(old_val)) + delta
    new_val = f"{new_num}.{rng.choice(['00', '50', '99'])}"

    font_size = max(16, int(min(width, height) * 0.035))
    font = load_font(font_size)

    x = int(width * rng.uniform(0.52, 0.78))
    y = int(height * rng.uniform(0.62, 0.86))

    old_box = draw.textbbox((x, y), old_val, font=font)
    new_box = draw.textbbox((x, y + int(font_size * 0.95)), new_val, font=font)
    left = min(old_box[0], new_box[0]) - 8
    top = min(old_box[1], new_box[1]) - 6
    right = max(old_box[2], new_box[2]) + 8
    bottom = max(old_box[3], new_box[3]) + 6

    draw.rectangle((left, top, right, bottom), fill=(245, 245, 245, 220))
    draw.text((x, y), old_val, font=font, fill=(45, 45, 45, 220))
    strike_y = (old_box[1] + old_box[3]) // 2
    draw.line((old_box[0] - 2, strike_y, old_box[2] + 2, strike_y), fill=(170, 35, 35, 230), width=2)
    draw.text((x, y + int(font_size * 0.95)), new_val, font=font, fill=(20, 20, 20, 230))

    return Image.alpha_composite(base, overlay).convert("RGB")


def apply_tamper_mode(image: Image.Image, rng: random.Random, mode: str) -> Image.Image:
    if mode == "brightness":
        return apply_brightness_tamper(image, rng)
    if mode == "duplicate_copy":
        return apply_duplicate_copy_tamper(image, rng)
    if mode == "number_overwrite":
        return apply_number_overwrite_tamper(image, rng)
    if mode == "handwritten":
        return draw_handwritten_overlay(image, rng)
    raise ValueError(f"Unsupported tamper mode: {mode}")


def output_path_for(
    input_file: Path,
    output_dir: Path,
    variant: int,
    count: int,
    name_suffix: str,
) -> Path:
    suffix = input_file.suffix.lower() if input_file.suffix else ".jpg"
    if count == 1:
        name = f"{input_file.stem}_{name_suffix}{suffix}"
    else:
        name = f"{input_file.stem}_{name_suffix}_{variant:02d}{suffix}"
    return output_dir / name


def run(
    input_path: Path,
    output_dir: Path,
    count: int,
    max_images: int,
    seed: int | None,
    modes: list[str],
    name_suffix: str,
) -> int:
    rng = random.Random(seed)
    images = discover_images(input_path, max_images=max_images)
    if not images:
        print(f"[WARN] No images found in: {input_path}")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for image_idx, image_path in enumerate(images):
        with Image.open(image_path) as img:
            for i in range(1, count + 1):
                mode_idx = ((image_idx * count) + (i - 1)) % len(modes)
                mode = modes[mode_idx]
                tampered = apply_tamper_mode(img, rng, mode)
                out_file = output_path_for(image_path, output_dir, i, count, name_suffix=name_suffix)
                save_kwargs = {}
                if out_file.suffix.lower() in {".jpg", ".jpeg", ".webp"}:
                    save_kwargs["quality"] = 95
                tampered.save(out_file, **save_kwargs)
                print(f"[OK][{mode}] {image_path} -> {out_file}")
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
    modes = parse_modes(args.modes)

    run(
        input_path=input_path,
        output_dir=output_dir,
        count=args.count,
        max_images=args.max_images,
        seed=args.seed,
        modes=modes,
        name_suffix=args.name_suffix,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
