"""Regenerates every number quoted in ocr.py's BLUR_* block.

Two things are measured:

  --scan   How many real receipts the gate refuses. No API calls. Use this to
           check a threshold change against the whole corpus in seconds.

  --probe  The calibration proper. Scores receipts and Gaussian-blurred copies,
           then actually sends each to Gemini and records whether extraction
           succeeded. This is the only honest target: the gate's job is to skip
           images the OCR cannot use, so the ground truth is what the OCR does,
           not what the image looks like. Costs one API call per sample.

Usage:
    ./.venv/bin/python calibrate_blur_gate.py --scan
    ./.venv/bin/python calibrate_blur_gate.py --probe --limit 12

Result on the corpus as of 20 Aug 2026: the old whole-frame measure refused
12/100 real receipts; this one refuses 0/100. The classes overlap so heavily
that no threshold separates them — Receipt 10 blurred to sigma 2.5 (score 80.7)
came back unreadable while the blurrier sigma 3.0 copy (score 49.5) extracted
fine. The threshold therefore sits below the lowest score that ever produced a
successful extraction, and Gemini decides everything above it.
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr  # noqa: E402  (path set above)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS = os.path.join(HERE, "..", "dataset", "indian")
SIGMAS = (1.8, 2.5, 4.0)


def scan(corpus):
    paths = sorted(glob.glob(os.path.join(corpus, "*.jpg")))
    if not paths:
        print(f"  no images in {corpus}")
        return
    rows = []
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        s = ocr._blur_score(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        rows.append((s, os.path.basename(p)))
    rows.sort()
    refused = [r for r in rows if r[0] < ocr.BLUR_THRESHOLD]
    arr = np.array([s for s, _ in rows])
    print(f"  corpus            : {len(rows)} images from {corpus}")
    print(f"  threshold         : {ocr.BLUR_THRESHOLD}")
    print(f"  refused pre-OCR   : {len(refused)}/{len(rows)} "
          f"({len(refused) / len(rows) * 100:.0f}%)")
    print(f"  score percentiles : min={arr.min():.0f} p5={np.percentile(arr, 5):.0f} "
          f"median={np.median(arr):.0f} max={arr.max():.0f}")
    print("\n  ten lowest-scoring images (the ones a threshold change moves first):")
    for s, n in rows[:10]:
        mark = "REFUSED" if s < ocr.BLUR_THRESHOLD else "admitted"
        print(f"    {n:<24} {s:10.1f}  {mark}")


def probe(corpus, limit):
    """Score, blur, and ask Gemini what it can actually read."""
    paths = sorted(glob.glob(os.path.join(corpus, "*.jpg")))
    scored = []
    for p in paths:
        img = cv2.imread(p)
        if img is not None:
            scored.append((ocr._blur_score(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)), p))
    scored.sort()
    # The lowest scorers are where the boundary is; anything high is not in doubt.
    sample = [p for _, p in scored[:limit]]

    original = ocr.BLUR_THRESHOLD
    ocr.BLUR_THRESHOLD = 0          # in-memory only, so the gate cannot pre-empt Gemini
    results = []
    try:
        import tempfile
        for src in sample:
            col = cv2.imread(src)
            variants = [(0.0, src)]
            for sig in SIGMAS:
                fd, tmp = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                cv2.imwrite(tmp, cv2.GaussianBlur(col, (0, 0), sig))
                variants.append((sig, tmp))
            for sig, path in variants:
                score = ocr._blur_score(cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY))
                try:
                    r = ocr.extract_receipt_data(path)
                except Exception as exc:                      # noqa: BLE001
                    r = {"error": f"exception: {exc}"}
                err = r.get("error")
                # multi_bill is a content verdict, not a legibility one.
                if err == "multi_bill_detected":
                    if sig:
                        os.unlink(path)
                    continue
                ok = (not err) and r.get("total") is not None
                results.append((score, ok))
                print(f"  {os.path.basename(src):<24} sigma={sig:<4} "
                      f"score={score:9.1f}  {'READABLE' if ok else 'failed'}", flush=True)
                if sig:
                    os.unlink(path)
    finally:
        ocr.BLUR_THRESHOLD = original

    if not results:
        return
    readable = [s for s, ok in results if ok]
    failed = [s for s, ok in results if not ok]
    print(f"\n  readable samples : {len(readable)}   lowest score {min(readable):.1f}")
    if failed:
        print(f"  failed samples   : {len(failed)}   highest score {max(failed):.1f}")
        if max(failed) > min(readable):
            print("  the classes OVERLAP — no threshold separates them; keep the gate")
            print("  below the lowest readable score and let Gemini judge the rest.")
    print(f"\n  current threshold {ocr.BLUR_THRESHOLD} would refuse "
          f"{sum(1 for s in readable if s < ocr.BLUR_THRESHOLD)} readable "
          f"and {sum(1 for s in failed if s < ocr.BLUR_THRESHOLD)} unreadable samples.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--scan", action="store_true", help="score the corpus, no API calls")
    ap.add_argument("--probe", action="store_true", help="calibrate against Gemini (costs calls)")
    ap.add_argument("--limit", type=int, default=10, help="receipts to probe (x4 variants)")
    a = ap.parse_args()
    if not (a.scan or a.probe):
        ap.error("choose --scan or --probe")
    if a.scan:
        scan(a.corpus)
    if a.probe:
        probe(a.corpus, a.limit)
