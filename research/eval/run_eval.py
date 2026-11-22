"""
Evaluation harness — runs a version of the pipeline over a labelled receipt set
and scores it field by field.

    research/.venv/bin/python research/eval/run_eval.py \
        --code-root .  --extractor oracle  --name after_dryrun
    research/.venv/bin/python research/eval/run_eval.py compare

EXTRACTORS
  oracle   --dry-run. The model call inside the code root's ml-service/ocr.py is
           replaced by a stub that returns the receipt's PRINTED strings verbatim
           (date as printed, total with its currency marker, Arabic merchant if
           that is what is printed). The currency field is returned only if that
           code root's prompt asks for one. Everything else in ocr.py runs for
           real, including its blur gate. This therefore measures the
           post-extraction pipeline under "the model copies what is printed" —
           NOT OCR accuracy. No API key is needed.
  gemini   Live. The code root's ocr.py calls the extraction model with
           GEMINI_API_KEY from the environment. --prompt selects an ablation.
  easyocr  Non-LLM baseline. EasyOCR (ar+en) reads the text and fixed rules pick
           out merchant, date, total and currency. The raw strings then go
           through the same backend normalisation as everything else.

Every extractor's output is normalised by the code root's OWN backend helpers
(research/eval/js_normalize.js), so a v1.0 root is scored with v1.0 code.
"""

import argparse
import csv
import importlib
import json
import os
import re
import subprocess
import sys
import time
import types
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_DATASET = os.path.join(REPO, "dataset", "gulf_synthetic", "gulf_synthetic.csv")
RESULTS_DIR = os.path.join(REPO, "research", "results")
sys.path.insert(0, HERE)

import prompts  # noqa: E402

BREAKDOWNS = ["currency", "language", "degradation", "digits"]
METRICS = ["merchant_exact", "merchant_fuzzy", "date_exact", "total_exact", "total_1pct",
           "currency_exact", "gate_correct", "receipt_success"]


# ── text helpers ────────────────────────────────────────────────────────────
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def norm_text(s):
    """Normalised form for merchant comparison: NFKC, casefold, Arabic alef and
    taa-marbuta folded, punctuation and whitespace removed."""
    s = unicodedata.normalize("NFKC", str(s or "")).casefold()
    s = re.sub("[أإآ]", "ا", s).replace("ة", "ه").replace("ـ", "")
    return re.sub(r"[\W_]+", "", s)


def fuzzy(a, b):
    from rapidfuzz import fuzz
    return fuzz.ratio(norm_text(a), norm_text(b)) / 100.0


# ── extractors ──────────────────────────────────────────────────────────────
def load_ocr(code_root):
    ml = os.path.join(os.path.abspath(code_root), "ml-service")
    sys.path.insert(0, ml)
    for name in ("ocr", "receipt_schema"):
        sys.modules.pop(name, None)
    return importlib.import_module("ocr")


def stub_model(ocr, reply_fn):
    """Replace only the network call; every other line of ocr.py runs."""
    holder = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            return types.SimpleNamespace(text=json.dumps(reply_fn(holder["row"]), ensure_ascii=False),
                                         candidates=[])

    ocr.api_key = "dry-run"
    ocr._API_KEYS = [("GEMINI_API_KEY", "dry-run")]
    ocr._KEY_STATE = {"GEMINI_API_KEY": {"client": None, "last_used": 0.0,
                                         "cooling_until": 0.0, "unsupported": set()}}
    ocr._client_for = lambda n, v: types.SimpleNamespace(models=FakeModels())
    ocr.RATE_LIMIT_INTERVAL = 0
    return holder


def oracle_reply(prompt_has_currency):
    def reply(row):
        printed_merchant = row["merchant_ar"] if row["language"] == "ar" and row["merchant_ar"] \
            else row["merchant"]
        out = {"rawMerchant": printed_merchant, "date": row["printed_date"],
               "total": row["printed_total"], "category": row["category"], "items": [],
               "handwritten_flag": False, "handwritten_details": None}
        if prompt_has_currency:
            out["currency"] = row["currency"]   # the ISO code of the printed marker
        return out
    return reply


class EasyOcrRules:
    """EasyOCR + hand-written rules. Deliberately simple: a floor, not a rival."""
    TOTAL_WORDS = re.compile(r"total|الاجمالي|الإجمالي|اجمالي|المجموع", re.I)
    DATE_RE = re.compile(r"\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}")
    AMOUNT_RE = re.compile(r"\d[\d,.٫٬]*")

    def __init__(self):
        import easyocr
        self.reader = easyocr.Reader(["ar", "en"], gpu=False, verbose=False)
        sys.path.insert(0, os.path.join(REPO, "ml-service"))
        from receipt_schema import detect_currency
        self.detect = detect_currency

    def lines(self, path):
        res = self.reader.readtext(path, detail=1, paragraph=False)
        rows = []
        for box, text, _conf in res:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            rows.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), text))
        rows.sort()
        grouped, current = [], []
        for r in rows:
            if current and abs(r[0] - current[-1][0]) > 0.6 * max(r[2], current[-1][2]):
                grouped.append(current)
                current = []
            current.append(r)
        if current:
            grouped.append(current)
        return [" ".join(t for _, _, _, t in sorted(g, key=lambda x: x[1])) for g in grouped]

    def __call__(self, path):
        lines = self.lines(path)
        text = "\n".join(lines)
        latin = text.translate(_ARABIC_DIGITS)
        merchant = lines[0] if lines else ""
        date = None
        for ln in lines:
            m = self.DATE_RE.search(ln.translate(_ARABIC_DIGITS))
            if m:
                date = m.group(0)
                break
        total_line = next((ln for ln in reversed(lines) if self.TOTAL_WORDS.search(ln)), None)
        total = None
        if total_line:
            amounts = self.AMOUNT_RE.findall(total_line.translate(_ARABIC_DIGITS))
            total = total_line if amounts else None
        currency = self.detect(total_line or "") or self.detect(latin)
        return {"rawMerchant": merchant, "date": date, "total": total, "currency": currency,
                "items": [], "_ocr_text": text}


# ── normalisation through the code root's backend ───────────────────────────
def normalise(code_root, extractions, supported):
    env = dict(os.environ)
    if supported:
        env["SUPPORTED_CURRENCIES"] = supported
    else:
        env.pop("SUPPORTED_CURRENCIES", None)
    payload = "\n".join(json.dumps({k: v for k, v in e.items() if not k.startswith("_")},
                                   ensure_ascii=False) for e in extractions) + "\n"
    out = subprocess.run(["node", os.path.join(HERE, "js_normalize.js"), code_root],
                         input=payload, capture_output=True, text=True, env=env, check=True)
    return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]


# ── scoring ─────────────────────────────────────────────────────────────────
def score(row, ext, norm, supported_list):
    gt_total = float(row["total_parsed"])
    merchants = [row["merchant"]] + ([row["merchant_ar"]] if row.get("merchant_ar") else [])
    pred_m = ext.get("rawMerchant") or ""
    m_exact = any(norm_text(pred_m) == norm_text(m) for m in merchants) if pred_m else False
    m_fuzzy = max((fuzzy(pred_m, m) for m in merchants), default=0) >= 0.85 if pred_m else False
    amt = norm["amount"]
    t_exact = amt is not None and abs(amt - gt_total) < 0.005
    t_1pct = amt is not None and abs(amt - gt_total) <= 0.01 * gt_total
    d_exact = norm["date_iso"] == row["date"]
    c_exact = norm["currency"] == row["currency"]
    should_accept = row["currency"] in supported_list
    accepted = norm["gate_status"] == "accepted"
    return {
        "merchant_exact": m_exact, "merchant_fuzzy": m_fuzzy, "date_exact": d_exact,
        "total_exact": t_exact, "total_1pct": t_1pct, "currency_exact": c_exact,
        "gate_correct": accepted == should_accept,
        "wrongly_accepted": accepted and not should_accept,
        "wrongly_rejected": (not accepted) and should_accept,
        "receipt_success": m_fuzzy and d_exact and t_exact and c_exact,
    }


def rate(rows, key):
    return sum(1 for r in rows if r[key] in (True, "True")) / len(rows) if rows else float("nan")


def summary_tables(results, title, notes):
    out = [f"# {title}", "", *notes, "", f"n = {len(results)}", "",
           "| metric | overall |", "|---|---|"]
    for m in METRICS + ["wrongly_accepted", "wrongly_rejected"]:
        out.append(f"| {m} | {rate(results, m):.3f} |")
    lat = sorted(float(r["latency_ms"]) for r in results)
    out.append(f"| latency_ms median | {lat[len(lat) // 2]:.1f} |")
    for dim in BREAKDOWNS:
        groups = defaultdict(list)
        for r in results:
            groups[r[dim]].append(r)
        out += ["", f"## By {dim}", "",
                "| " + dim + " | n | " + " | ".join(METRICS) + " |",
                "|---|---|" + "---|" * len(METRICS)]
        for g in sorted(groups):
            rs = groups[g]
            out.append(f"| {g} | {len(rs)} | " + " | ".join(f"{rate(rs, m):.2f}" for m in METRICS) + " |")
    return "\n".join(out) + "\n"


def run(args):
    import matplotlib
    matplotlib.use("Agg")
    rows = list(csv.DictReader(open(args.dataset, encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    supported_list = [c.strip().upper() for c in (args.supported or "INR").split(",") if c.strip()]

    code_root = os.path.abspath(args.code_root)
    # Checked BEFORE ocr.py is imported: that module loads ml-service/.env, so a
    # check made afterwards would find a developer's local keys and make live,
    # billed calls that nobody asked for. A live run must export the key itself.
    if args.extractor == "gemini" and not any(
            k.startswith("GEMINI_API_KEY") and os.environ[k].strip() for k in os.environ):
        sys.exit("GEMINI_API_KEY is not set in the environment — export it for a live run, "
                 "or use --dry-run.")
    if args.extractor == "easyocr":
        extract = EasyOcrRules()
        call = lambda row, path: extract(path)
    else:
        ocr = load_ocr(code_root)
        if args.prompt != "as_is":
            ocr.RECEIPT_PROMPT = prompts.VARIANTS[args.prompt]
        if args.extractor == "oracle":
            holder = stub_model(ocr, oracle_reply('"currency"' in ocr.RECEIPT_PROMPT))
        else:
            holder = {}

        def call(row, path):
            holder["row"] = row
            res = ocr.extract_receipt_data(path)
            return prompts.coerce_keys(res) if args.prompt == "no_schema" else res

    extractions, latencies = [], []
    for row in rows:
        path = os.path.join(REPO, row["image_path"])
        t0 = time.perf_counter()
        try:
            ext = call(row, path)
        except Exception as e:                       # a crash is a result, not an abort
            ext = {"error": f"EXCEPTION: {e}"}
        latencies.append((time.perf_counter() - t0) * 1000)
        extractions.append(ext if isinstance(ext, dict) else {"error": "non-dict response"})

    t0 = time.perf_counter()
    norms = normalise(code_root, extractions, args.supported)
    norm_ms = (time.perf_counter() - t0) * 1000 / max(1, len(rows))

    results = []
    for row, ext, norm, lat in zip(rows, extractions, norms, latencies):
        s = score(row, ext, norm, supported_list)
        results.append({
            "image_path": row["image_path"], "currency": row["currency"],
            "language": row["language"], "degradation": row["degradation"],
            "digits": row["digits"], "source": row["source"],
            "gt_total": row["total_parsed"], "gt_date": row["date"],
            "pred_merchant": ext.get("rawMerchant"), "pred_total_raw": ext.get("total"),
            "pred_amount": norm["amount"], "pred_date": norm["date_iso"],
            "pred_currency": norm["currency"], "gate_status": norm["gate_status"],
            "gate_error": norm["gate_error"], "ocr_error": ext.get("error"),
            "normaliser": norm["normaliser"], "latency_ms": round(lat + norm_ms, 2), **s,
        })

    out_dir = os.path.join(RESULTS_DIR, args.name)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    notes = [f"- extractor: `{args.extractor}`, prompt: `{args.prompt}`, normaliser: "
             f"`{results[0]['normaliser']}`, supported currencies: `{','.join(supported_list)}`",
             f"- dataset: `{os.path.relpath(args.dataset, REPO)}` — **SYNTHETIC**",
             "- latency is wall time for extraction + normalisation on this machine"
             + (" — the model call is stubbed, so it EXCLUDES model time" if args.extractor == "oracle" else "")]
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(summary_tables(results, f"Evaluation: {args.name}", notes))
    chart_breakdown(results, out_dir, args.name)
    print(f"[{args.name}] receipt_success={rate(results, 'receipt_success'):.3f} "
          f"gate_correct={rate(results, 'gate_correct'):.3f} → {os.path.relpath(out_dir, REPO)}")


def chart_breakdown(results, out_dir, name):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for ax, dim in zip(axes, ["currency", "degradation"]):
        groups = defaultdict(list)
        for r in results:
            groups[r[dim]].append(r)
        keys = sorted(groups)
        ax.bar(keys, [rate(groups[k], "receipt_success") for k in keys], color="#3b6ea5")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"receipt success by {dim}", fontsize=10)
        ax.tick_params(labelsize=8)
    fig.suptitle(f"{name} (synthetic set)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "breakdown.png"), dpi=150)
    plt.close(fig)


# ── comparison across runs ──────────────────────────────────────────────────
def compare(args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    runs = [r for r in args.runs if os.path.exists(os.path.join(RESULTS_DIR, r, "results.csv"))]
    data = {r: list(csv.DictReader(open(os.path.join(RESULTS_DIR, r, "results.csv"), encoding="utf-8")))
            for r in runs}
    shown = METRICS + ["wrongly_accepted"]
    lines = ["# Comparison (synthetic set — not real-data accuracy)", "",
             "| run | n | " + " | ".join(shown) + " |", "|---|---|" + "---|" * len(shown)]
    for r in runs:
        lines.append(f"| {r} | {len(data[r])} | " + " | ".join(f"{rate(data[r], m):.3f}" for m in shown) + " |")
    missing = [r for r in args.runs if r not in runs]
    if missing:
        lines += ["", "Not run (no results): " + ", ".join(f"`{m}`" for m in missing)]
    for dim in ("currency", "language", "digits", "degradation"):
        keys = sorted({row[dim] for r in runs for row in data[r]})
        lines += ["", f"## receipt_success by {dim}", "",
                  "| run | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
        for r in runs:
            cells = []
            for k in keys:
                rs = [x for x in data[r] if x[dim] == k]
                cells.append(f"{rate(rs, 'receipt_success'):.2f}")
            lines.append(f"| {r} | " + " | ".join(cells) + " |")
    with open(os.path.join(RESULTS_DIR, "comparison.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    fields = ["date_exact", "total_exact", "currency_exact", "gate_correct", "receipt_success"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    width = 0.8 / max(1, len(runs))
    palette = ["#9aa5b1", "#3b6ea5", "#d08c2f", "#5a9e6f"]
    for i, r in enumerate(runs):
        ax.bar([j + i * width for j in range(len(fields))], [rate(data[r], f) for f in fields],
               width, label=r, color=palette[i % len(palette)])
    ax.set_xticks([j + width * (len(runs) - 1) / 2 for j in range(len(fields))])
    ax.set_xticklabels(fields, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("Field accuracy per run (48 synthetic receipts)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "comparison.png"), dpi=150)
    plt.close(fig)
    print("\n".join(lines[:4 + len(runs)]))


def main():
    ap = argparse.ArgumentParser(description="Receipt pipeline evaluation harness")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("compare")
    c.add_argument("runs", nargs="*", default=["before_v1.0_dryrun", "after_dryrun",
                                               "baseline_easyocr", "after_gemini_live"])
    ap.add_argument("--code-root", default=REPO)
    ap.add_argument("--extractor", choices=["oracle", "gemini", "easyocr"], default="oracle")
    ap.add_argument("--dry-run", action="store_true", help="alias for --extractor oracle")
    ap.add_argument("--prompt", choices=["as_is"] + list(prompts.VARIANTS), default="as_is")
    ap.add_argument("--dataset", default=DEFAULT_DATASET)
    ap.add_argument("--supported", default=None, help="SUPPORTED_CURRENCIES for the gate (default INR)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--name", default="run")
    args = ap.parse_args()
    if args.cmd == "compare":
        return compare(args)
    if args.dry_run:
        args.extractor = "oracle"
    run(args)


if __name__ == "__main__":
    main()
