import os
import json
from ocr import extract_receipt_data

TEST_BILLS_DIR = "../dataset/test_bills"

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
            "failure_reason": None
        },
        "data": {}
    }
    
    stopped_early = False
    
    for image_name in images:
        image_path = os.path.join(TEST_BILLS_DIR, image_name)
        print(f"Processing: {image_name}...")
        
        data = extract_receipt_data(image_path)
        
        # Check if the extraction was a terminal failure
        if isinstance(data, dict) and (data.get("error") == "TERMINAL_FAILURE" or data.get("error") == "SYSTEM_FAILURE"):
            print(f"\n[FATAL] Stopping iteration: {data.get('message')}")
            results["metadata"]["failure_reason"] = f"Failed on {image_name}: {data.get('message')}"
            stopped_early = True
            break
            
        results["data"][image_name] = data
        results["metadata"]["processed_count"] += 1
        
        print(f"Result for {image_name}:")
        print(json.dumps(data, indent=2))
        print("-" * 30)

    if not stopped_early:
        results["metadata"]["status"] = "COMPLETED"
    
    # Save results to a file
    with open("ocr_test_results.json", "w") as f:
        json.dump(results, f, indent=4)
    
    print(f"\n[DONE] Test results saved to ml-service/ocr_test_results.json")
    if stopped_early:
        print("[NOTE] Test stopped early due to an error. Check the metadata in the JSON file.")

if __name__ == "__main__":
    run_test()
