import os
import json
import hashlib
from ocr import extract_receipt_data

TEST_BILLS_DIR = "../dataset/test_bills"
RESULTS_FILE = "ocr_test_results.json"


def generate_receipt_fingerprint(merchant, date, total):
    """
    Deterministic fingerprint matching the same logic used in server.js.
    merchant|date|total(2dp) → SHA-256 hex digest.
    """
    raw = f"{str(merchant).strip().lower()}|{str(date).strip()}|{float(total):.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()


def load_existing_fingerprints():
    """Load fingerprints already recorded in the results file to avoid reprocessing."""
    if not os.path.exists(RESULTS_FILE):
        return set()
    try:
        with open(RESULTS_FILE) as f:
            saved = json.load(f)
        fingerprints = set()
        for entry in saved.get("data", {}).values():
            if isinstance(entry, dict) and not entry.get("error"):
                fp = entry.get("receipt_fingerprint")
                if fp:
                    fingerprints.add(fp)
        return fingerprints
    except Exception:
        return set()


def run_test():
    if not os.path.exists(TEST_BILLS_DIR):
        print(f"[ERROR] Directory not found: {TEST_BILLS_DIR}")
        return

    images = sorted([f for f in os.listdir(TEST_BILLS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if not images:
        print(f"[INFO] No images found in {TEST_BILLS_DIR}.")
        return

    print(f"--- Starting OCR Test on {len(images)} bills ---\n")

    results = {
        "metadata": {
            "status": "INCOMPLETE",
            "total_images": len(images),
            "processed_count": 0,
            "skipped_duplicates": 0,
            "failure_reason": None
        },
        "data": {}
    }

    # Build fingerprint set from previously saved results to prevent re-processing
    seen_fingerprints = load_existing_fingerprints()
    stopped_early = False

    for image_name in images:
        image_path = os.path.join(TEST_BILLS_DIR, image_name)
        print(f"Processing: {image_name}...")

        data = extract_receipt_data(image_path)

        # Terminal failures stop the run
        if isinstance(data, dict) and data.get("error") in ("TERMINAL_FAILURE", "SYSTEM_FAILURE"):
            print(f"\n[FATAL] Stopping iteration: {data.get('message')}")
            results["metadata"]["failure_reason"] = f"Failed on {image_name}: {data.get('message')}"
            stopped_early = True
            break

        # Unreadable / blur rejection — record but do not fingerprint
        if isinstance(data, dict) and data.get("error") == "unreadable":
            results["data"][image_name] = data
            results["metadata"]["processed_count"] += 1
            print(f"[WARN] {image_name} rejected as unreadable.")
            print("-" * 30)
            continue

        # Duplicate detection — mirrors server.js generateReceiptFingerprint logic
        if isinstance(data, dict) and not data.get("error"):
            fp = generate_receipt_fingerprint(
                data.get("rawMerchant", ""),
                data.get("date", ""),
                data.get("total", 0)
            )
            data["receipt_fingerprint"] = fp

            if fp in seen_fingerprints:
                print(f"[SKIP] {image_name} — duplicate receipt (fingerprint already seen), skipping.")
                results["data"][image_name] = {
                    "skipped": True,
                    "reason": "duplicate_receipt",
                    "receipt_fingerprint": fp
                }
                results["metadata"]["skipped_duplicates"] += 1
                continue

            seen_fingerprints.add(fp)

        results["data"][image_name] = data
        results["metadata"]["processed_count"] += 1

        print(f"Result for {image_name}:")
        print(json.dumps(data, indent=2))
        print("-" * 30)

    if not stopped_early:
        results["metadata"]["status"] = "COMPLETED"

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\n[DONE] Test results saved to ml-service/{RESULTS_FILE}")
    if stopped_early:
        print("[NOTE] Test stopped early due to an error. Check metadata in the JSON file.")

if __name__ == "__main__":
    run_test()
