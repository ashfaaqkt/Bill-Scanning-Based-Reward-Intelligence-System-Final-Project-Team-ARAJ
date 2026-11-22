"""The synthetic set must be a pure function of (n, seed)."""
import filecmp
import hashlib
import os

import generate


def _digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_same_seed_same_csv_and_images(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate.generate(n=8, seed=7, out_csv=str(a / "x.csv"), image_dir=str(a)) if a.mkdir() is None else None
    generate.generate(n=8, seed=7, out_csv=str(b / "x.csv"), image_dir=str(b)) if b.mkdir() is None else None
    assert filecmp.cmp(a / "x.csv", b / "x.csv", shallow=False)
    for name in sorted(os.listdir(a)):
        if name.endswith(".png"):
            assert _digest(a / name) == _digest(b / name), name


def test_different_seed_differs(tmp_path):
    rows1 = generate.generate(n=8, seed=1, out_csv=str(tmp_path / "1.csv"), image_dir=str(tmp_path), write_images=False)
    rows2 = generate.generate(n=8, seed=2, out_csv=str(tmp_path / "2.csv"), image_dir=str(tmp_path), write_images=False)
    assert [r["total"] for r in rows1] != [r["total"] for r in rows2]


def test_every_row_is_marked_synthetic(tmp_path):
    rows = generate.generate(n=12, seed=2026, out_csv=str(tmp_path / "s.csv"), image_dir=str(tmp_path), write_images=False)
    assert all(r["source"] == "synthetic" and "SYNTHETIC" in r["notes"] for r in rows)
    assert {r["currency"] for r in rows} == {"SAR", "AED", "QAR", "INR"}


def test_committed_csv_matches_default_seed(tmp_path):
    """The tracked CSV is exactly what `make data` regenerates."""
    out = tmp_path / "regen.csv"
    generate.generate(out_csv=str(out), image_dir=str(tmp_path), write_images=False)
    assert filecmp.cmp(out, generate.CSV_PATH, shallow=False)
