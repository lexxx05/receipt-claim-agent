"""
script to check the ground truth receipt and image receipt
purpose: data understanding
"""
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORD_DIR = PROJECT_ROOT / "data" / "CORD"

def load_record(split: str, image_id: int) -> dict:
    """
    Find ONE receipt on JSONL file
    """
    jsonl_path = CORD_DIR / "gt" / f"{split}.jsonl"
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record['image_id'] == image_id:
                return record
    raise SystemExit(f"[ERROR] image_id {image_id} tidak ada di {jsonl_path.name}")

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Pakai: python scripts\\show_receipt.py <dev|test> <image_id>")

    split, image_id = sys.argv[1], int(sys.argv[2])
    record = load_record(split, image_id)
    image_path = CORD_DIR / record['image_file'] # slicing image_file doang, karna jsonl ada gtnya
    meta = record['ground_truth']['meta']

    print(f"[INFO] Gambar : {image_path}")
    print(f"[INFO] Ukuran : {meta['image_size']['width']}x{meta['image_size']['height']}")
    print(json.dumps(record["ground_truth"]["gt_parse"], indent=2, ensure_ascii=False))

    if hasattr(os, "startfile"):
        os.startfile(image_path)

if __name__ == "__main__":
    main()
