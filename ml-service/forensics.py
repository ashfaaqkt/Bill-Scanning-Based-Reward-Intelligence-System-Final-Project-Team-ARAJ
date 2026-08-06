"""
Image forensics feature extractor — Owner: Ashfaaq KT

Hand-designed tamper signals, as a counterpart to the CNN. With only 194
labelled receipts a CNN is data-starved, but forensic features are computed
per image rather than learned, so a small dataset barely hurts them.

Each feature group targets a specific manipulation produced by
dataset/generate_tampered.py:

  brightness        -> local luminance discontinuity  (BRIGHTNESS group)
  duplicate_copy    -> repeated image regions         (COPY-MOVE group)
  number_overwrite  -> synthetic text spliced on top  (ELA / SHARPNESS groups)
  handwritten       -> coloured ink overlay           (ELA / COLOUR groups)

Every extractor returns plain floats so the whole set can go straight into a
gradient-boosted classifier. No OpenCV dependency — NumPy, SciPy and Pillow only.
"""

from io import BytesIO

import numpy as np
from PIL import Image
from scipy.ndimage import laplace, median_filter, uniform_filter

MAX_SIDE = 768        # downscale long edge before analysis, for speed
ELA_QUALITY = 90      # re-save quality for Error Level Analysis
BLOCK = 16            # block size for local-statistic features
EPS = 1e-6


# ── HELPERS ────────────────────────────────────────────────────
def _block_stats(array, block=BLOCK):
    """Mean and standard deviation over non-overlapping block x block tiles."""
    height, width = array.shape
    rows, cols = height // block, width // block
    if rows < 2 or cols < 2:
        return np.array([array.mean()]), np.array([array.std()])

    trimmed = array[:rows * block, :cols * block]
    tiles = trimmed.reshape(rows, block, cols, block).transpose(0, 2, 1, 3)
    tiles = tiles.reshape(rows * cols, block * block)
    return tiles.mean(axis=1), tiles.std(axis=1)


def _spread(values):
    """Dispersion summary — tampering shows up as inconsistency across blocks."""
    values = np.asarray(values, dtype=np.float64)
    median = np.median(values)
    return {
        "std": float(values.std()),
        "range": float(values.max() - values.min()),
        "ratio": float(values.max() / (median + EPS)),
    }


# ── FEATURE GROUPS ─────────────────────────────────────────────
def ela_features(image):
    """
    Error Level Analysis. Re-saving a JPEG re-quantises every region; areas that
    were pasted or drawn on have a different compression history and so change
    by a different amount. Classic splice detector.
    """
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=ELA_QUALITY)
    buffer.seek(0)
    with Image.open(buffer) as resaved:
        difference = np.abs(np.asarray(image, dtype=np.float32)
                            - np.asarray(resaved.convert("RGB"), dtype=np.float32))

    ela = difference.max(axis=2)
    block_means, _ = _block_stats(ela)
    spread = _spread(block_means)

    return {
        "ela_mean": float(ela.mean()),
        "ela_std": float(ela.std()),
        "ela_p95": float(np.percentile(ela, 95)),
        "ela_p99": float(np.percentile(ela, 99)),
        "ela_max": float(ela.max()),
        "ela_frac_high": float((ela > 15).mean()),
        "ela_block_std": spread["std"],
        "ela_block_ratio": spread["ratio"],
    }


def noise_features(gray):
    """
    Noise-residual consistency. A camera imposes a uniform sensor-noise floor.
    Pasted or synthetically drawn content carries different noise, so the
    residual becomes inconsistent from block to block.
    """
    residual = gray - median_filter(gray, size=3)
    _, block_stds = _block_stats(residual)
    spread = _spread(block_stds)

    centred = residual - residual.mean()
    variance = centred.var() + EPS
    kurtosis = float((centred ** 4).mean() / (variance ** 2))

    return {
        "noise_mean_abs": float(np.abs(residual).mean()),
        "noise_global_std": float(residual.std()),
        "noise_block_std_std": spread["std"],
        "noise_block_std_ratio": spread["ratio"],
        "noise_kurtosis": kurtosis,
    }


def blockiness_features(gray):
    """
    JPEG 8x8 grid alignment. An unedited JPEG has discontinuities on the grid
    boundary. Content pasted at an arbitrary offset, or re-encoded after an
    edit, disturbs that alignment.
    """
    horizontal = np.abs(np.diff(gray, axis=1))
    vertical = np.abs(np.diff(gray, axis=0))

    def grid_ratio(diff, axis):
        length = diff.shape[axis]
        index = np.arange(length)
        on_grid = (index % 8) == 7
        if on_grid.sum() == 0 or (~on_grid).sum() == 0:
            return 1.0
        taken = diff[:, on_grid] if axis == 1 else diff[on_grid, :]
        rest = diff[:, ~on_grid] if axis == 1 else diff[~on_grid, :]
        return float(taken.mean() / (rest.mean() + EPS))

    return {
        "block_ratio_h": grid_ratio(horizontal, 1),
        "block_ratio_v": grid_ratio(vertical, 0),
        "block_energy": float(horizontal.mean() + vertical.mean()),
    }


def copy_move_features(gray):
    """
    Copy-move detection. Compares low-resolution block descriptors and counts
    near-identical pairs that sit far apart in the image — the signature of a
    region duplicated elsewhere, which is exactly the duplicate_copy mode.
    """
    scale = 256.0 / max(gray.shape)
    if scale < 1.0:
        target = (max(int(gray.shape[0] * scale), 32), max(int(gray.shape[1] * scale), 32))
        small = np.asarray(Image.fromarray(gray.astype(np.uint8)).resize(
            (target[1], target[0]), Image.BILINEAR), dtype=np.float32)
    else:
        small = gray

    step, size = 8, 16
    height, width = small.shape
    if height < size + step or width < size + step:
        return {"cm_pairs": 0.0, "cm_max_sim": 0.0, "cm_frac": 0.0}

    smoothed = uniform_filter(small, size=4)
    descriptors, positions = [], []
    for y in range(0, height - size, step):
        for x in range(0, width - size, step):
            patch = smoothed[y:y + size, x:x + size]
            pooled = patch.reshape(4, 4, 4, 4).mean(axis=(1, 3)).ravel()
            # Ignore flat blank paper — it duplicates trivially and means nothing.
            if pooled.std() < 2.0:
                continue
            descriptors.append(pooled - pooled.mean())
            positions.append((y, x))

    if len(descriptors) < 8:
        return {"cm_pairs": 0.0, "cm_max_sim": 0.0, "cm_frac": 0.0}

    matrix = np.asarray(descriptors, dtype=np.float32)
    matrix /= (np.linalg.norm(matrix, axis=1, keepdims=True) + EPS)
    similarity = matrix @ matrix.T

    coordinates = np.asarray(positions, dtype=np.float32)
    distance = np.sqrt(((coordinates[:, None, :] - coordinates[None, :, :]) ** 2).sum(-1))

    valid = (distance > 24) & np.triu(np.ones_like(similarity, dtype=bool), k=1)
    scores = similarity[valid]
    if scores.size == 0:
        return {"cm_pairs": 0.0, "cm_max_sim": 0.0, "cm_frac": 0.0}

    return {
        "cm_pairs": float((scores > 0.97).sum()),
        "cm_max_sim": float(scores.max()),
        "cm_frac": float((scores > 0.97).mean()),
    }


def brightness_features(gray):
    """
    Local luminance consistency — targets the brightness tamper mode, which
    lifts or drops a region and leaves a step the eye may miss.
    """
    block_means, _ = _block_stats(gray, block=32)
    spread = _spread(block_means)
    global_std = gray.std() + EPS

    return {
        "bright_block_std": spread["std"],
        "bright_block_range": spread["range"],
        "bright_max_dev": float(np.abs(block_means - gray.mean()).max() / global_std),
        "bright_global_mean": float(gray.mean()),
    }


def sharpness_features(gray):
    """
    Sharpness consistency. Text rendered by a drawing library has perfectly
    crisp edges, unlike photographed print which carries lens blur — so an
    overwritten total is locally sharper than its surroundings.
    """
    edges = laplace(gray)
    _, block_stds = _block_stats(np.abs(edges))
    spread = _spread(block_stds)

    return {
        "sharp_global_var": float(edges.var()),
        "sharp_block_std": spread["std"],
        "sharp_block_ratio": spread["ratio"],
        "edge_density": float((np.abs(edges) > 20).mean()),
    }


def colour_features(image):
    """
    Saturation statistics — receipts are near-greyscale, so coloured overlay
    ink from the handwritten mode stands out sharply.
    """
    hsv = np.asarray(image.convert("HSV"), dtype=np.float32)
    saturation = hsv[:, :, 1]

    return {
        "sat_mean": float(saturation.mean()),
        "sat_std": float(saturation.std()),
        "sat_p99": float(np.percentile(saturation, 99)),
        "sat_frac_high": float((saturation > 80).mean()),
    }


# ── PUBLIC API ─────────────────────────────────────────────────
def extract_features(image_path):
    """Returns the full forensic feature dict for one image."""
    with Image.open(image_path) as handle:
        image = handle.convert("RGB")
        if max(image.size) > MAX_SIDE:
            ratio = MAX_SIDE / max(image.size)
            image = image.resize((max(int(image.width * ratio), 32),
                                  max(int(image.height * ratio), 32)), Image.BILINEAR)
        image.load()

    gray = np.asarray(image.convert("L"), dtype=np.float32)

    features = {}
    features.update(ela_features(image))
    features.update(noise_features(gray))
    features.update(blockiness_features(gray))
    features.update(copy_move_features(gray))
    features.update(brightness_features(gray))
    features.update(sharpness_features(gray))
    features.update(colour_features(image))
    return features


def feature_vector(image_path, names=None):
    """Returns (vector, names) — stable ordering for model input."""
    features = extract_features(image_path)
    names = names or sorted(features)
    return np.array([features[n] for n in names], dtype=np.float32), names
