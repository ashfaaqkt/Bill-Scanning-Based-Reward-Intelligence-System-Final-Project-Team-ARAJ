"""The harness runs end to end with no API key (oracle extraction)."""
import csv
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_dry_run_produces_outputs(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GEMINI_API_KEY")}
    name = "_pytest_dryrun"
    subprocess.run([sys.executable, os.path.join(REPO, "research", "eval", "run_eval.py"),
                    "--dry-run", "--limit", "8", "--name", name],
                   check=True, cwd=REPO, env=env, capture_output=True)
    out = os.path.join(REPO, "research", "results", name)
    try:
        rows = list(csv.DictReader(open(os.path.join(out, "results.csv"), encoding="utf-8")))
        assert len(rows) == 8
        assert os.path.exists(os.path.join(out, "summary.md"))
        assert os.path.exists(os.path.join(out, "breakdown.png"))
        # On main's code the gate refuses every non-INR receipt it can read.
        for r in rows:
            if r["currency"] != "INR" and r["gate_status"] not in ("rejected_ocr",):
                assert r["gate_status"] == "rejected_currency", r
    finally:
        import shutil
        shutil.rmtree(out, ignore_errors=True)


def test_live_mode_refuses_without_key():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GEMINI_API_KEY")}
    p = subprocess.run([sys.executable, os.path.join(REPO, "research", "eval", "run_eval.py"),
                        "--extractor", "gemini", "--limit", "1", "--name", "_nokey"],
                       cwd=REPO, env=env, capture_output=True, text=True)
    assert p.returncode != 0 and "GEMINI_API_KEY" in (p.stderr + p.stdout)
