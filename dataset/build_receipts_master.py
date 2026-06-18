import os
import csv
import json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    
    cord_json_dir = root / "temp_cord" / "json"
    sroie_entities_dir = root / "temp_sroie" / "entities"
    processed_labels_csv = root / "processed" / "processed_labels_arpan.csv"
    output_csv = root / "processed" / "receipts_master.csv"
    
    records = []
    
    # 1. Parse CORD JSON files
    if cord_json_dir.exists():
        print("Parsing CORD JSON files...")
        cord_files = list(cord_json_dir.glob("*.json"))
        print(f"Found {len(cord_files)} CORD files.")
        for fpath in cord_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract total
                total = ""
                gt_parse = data.get("gt_parse", {})
                if "total" in gt_parse and "total_price" in gt_parse["total"]:
                    total = gt_parse["total"]["total_price"]
                elif "sub_total" in gt_parse and "subtotal_price" in gt_parse["sub_total"]:
                    total = gt_parse["sub_total"]["subtotal_price"]
                
                # Extract items_text
                items = []
                if "menu" in gt_parse and isinstance(gt_parse["menu"], list):
                    for item in gt_parse["menu"]:
                        nm = item.get("nm", "")
                        cnt = item.get("cnt", "")
                        if nm:
                            if cnt:
                                items.append(f"{nm} ({cnt})")
                            else:
                                items.append(nm)
                items_text = ", ".join(items)
                
                records.append({
                    "image_path": f"dataset/temp_cord/image/{fpath.name.replace('.json', '.png')}",
                    "merchant": "UNKNOWN",
                    "date": "",
                    "total": total,
                    "category": "restaurant",
                    "items_text": items_text,
                    "source": "CORD"
                })
            except Exception as e:
                print(f"Error parsing CORD file {fpath.name}: {e}")
                
    # 2. Parse SROIE text files
    if sroie_entities_dir.exists():
        print("Parsing SROIE entity files...")
        sroie_files = list(sroie_entities_dir.glob("*.txt"))
        print(f"Found {len(sroie_files)} SROIE files.")
        for fpath in sroie_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                merchant = data.get("company", "UNKNOWN")
                date = data.get("date", "")
                total = data.get("total", "")
                address = data.get("address", "")
                
                records.append({
                    "image_path": f"dataset/temp_sroie/image/{fpath.name.replace('.txt', '.jpg')}",
                    "merchant": merchant,
                    "date": date,
                    "total": total,
                    "category": "retail",
                    "items_text": address,
                    "source": "SROIE"
                })
            except Exception as e:
                print(f"Error parsing SROIE file {fpath.name}: {e}")
                
    # 3. Read processed_labels_arpan.csv
    if processed_labels_csv.exists():
        print("Parsing processed_labels_arpan.csv...")
        try:
            with open(processed_labels_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        "image_path": row.get("image_path", ""),
                        "merchant": "UNKNOWN",
                        "date": "",
                        "total": "",
                        "category": row.get("label", ""),
                        "items_text": row.get("arpan_flags", ""),
                        "source": "processed_labels_arpan"
                    })
            print(f"Appended records from processed_labels_arpan.csv.")
        except Exception as e:
            print(f"Error reading processed_labels_arpan.csv: {e}")
            
    # 4. Save to receipts_master.csv
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["image_path", "merchant", "date", "total", "category", "items_text", "source"]
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"Successfully wrote {len(records)} records to {output_csv}")
    except Exception as e:
        print(f"Error writing to receipts_master.csv: {e}")

if __name__ == "__main__":
    main()
