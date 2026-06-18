import os
import json
import urllib.request
from pathlib import Path
import pyarrow.parquet as pq
import fsspec

def get_hf_parquet_files(dataset_id):
    api_url = f"https://huggingface.co/api/datasets/{dataset_id}"
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            siblings = data.get('siblings', [])
            return [s['rfilename'] for s in siblings if s['rfilename'].endswith('.parquet')]
    except Exception as e:
        print(f"Error fetching Hugging Face file list for {dataset_id}: {e}")
        return []

def main():
    root = Path(__file__).resolve().parent
    fs = fsspec.filesystem('http')
    
    # 1. Download CORD annotations (json/ folder)
    cord_dir = root / "temp_cord" / "json"
    cord_dir.mkdir(parents=True, exist_ok=True)
    print("Fetching CORD dataset file list from HF API...")
    cord_files = get_hf_parquet_files("naver-clova-ix/cord-v1")
    train_cord_files = [f for f in cord_files if "data/train-" in f]
    print(f"Found {len(train_cord_files)} CORD training parquet files. Extracting ground truth JSONs...")
    
    cord_count = 0
    for filename in train_cord_files:
        url = f"https://huggingface.co/datasets/naver-clova-ix/cord-v1/resolve/main/{filename}"
        print(f"Reading {filename}...")
        try:
            with fs.open(url) as f:
                tbl = pq.read_table(f, columns=['ground_truth'])
                rows = tbl.to_pylist()
                for row in rows:
                    gt_json = json.loads(row['ground_truth'])
                    image_id = gt_json.get('meta', {}).get('image_id', cord_count)
                    out_filename = f"receipt_{image_id:05d}.json"
                    
                    with open(cord_dir / out_filename, 'w', encoding='utf-8') as out_f:
                        json.dump(gt_json, out_f, ensure_ascii=False, indent=4)
                    cord_count += 1
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    print(f"Successfully saved {cord_count} CORD JSON files to {cord_dir}")
    
    # 2. Download SROIE annotations (entities/ folder)
    sroie_dir = root / "temp_sroie" / "entities"
    sroie_dir.mkdir(parents=True, exist_ok=True)
    print("Fetching SROIE dataset file list from HF API...")
    sroie_files = get_hf_parquet_files("rth/sroie-2019-v2")
    print(f"Found SROIE parquet files: {sroie_files}. Extracting entities...")
    
    sroie_count = 0
    for filename in sroie_files:
        url = f"https://huggingface.co/datasets/rth/sroie-2019-v2/resolve/main/{filename}"
        print(f"Reading {filename}...")
        try:
            with fs.open(url) as f:
                tbl = pq.read_table(f, columns=['image', 'objects'])
                rows = tbl.to_pylist()
                for row in rows:
                    img_path_str = row['image']['path']
                    img_name = Path(img_path_str).stem
                    txt_filename = f"{img_name}.txt"
                    
                    entities = row['objects']['entities']
                    
                    with open(sroie_dir / txt_filename, 'w', encoding='utf-8') as out_f:
                        json.dump(entities, out_f, ensure_ascii=False, indent=4)
                    sroie_count += 1
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    print(f"Successfully saved {sroie_count} SROIE entities files to {sroie_dir}")

if __name__ == "__main__":
    main()
