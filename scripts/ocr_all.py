import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
from paddleocr import PaddleOCR 

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORD_DIR = PROJECT_ROOT / "data" / "CORD"
CACHE_DIR = PROJECT_ROOT / "data" / "ocr_cache"
LOG_PATH = CACHE_DIR / "ocr_log.csv"

SPLITS = ["dev", "test"]
LOG_FIELDS = [
    "timestamp", 
    "split", 
    "image_id", 
    "width", 
    "height",
    "seconds", 
    "n_texts", 
    "status",
    "error"
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch OCR CORD dengan PaddleOCR")
    parser.add_argument("--splits", nargs="+", choices=SPLITS, default=SPLITS,
                        help="Process Split (default: dev test)")
    parser.add_argument("--limit", type=int, default=None,
                        help="limit the number of picture per split")
    return parser.parse_args()

def load_records(split: str) -> list[dict]:
    """
    This function aims to read the receipt list from ONE JSONL as T1 result
    """
    jsonl_path = CORD_DIR / "gt" / f"{split}.jsonl"
    with jsonl_path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def cache_path(split: str, image_id: int):
    """
    This function aims to return the cache file location for ONE IMAGE
    """
    return CACHE_DIR / split / f"{image_id:04d}_res.json"

def is_valid_cache(path: Path) -> bool:
    """
    This function aims to check is the cache already developed with the uncorrupt size
    """
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return "rec_texts" in data
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False

def append_log(row: dict) -> None:
    """
    This function aims to append one observation (image) to a CSV log
    """
    is_new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)

def run_one(ocr: PaddleOCR, split: str, record: dict) -> dict:
    image_id = record["image_id"]
    image_path = CORD_DIR / record['image_file']
    size = record['ground_truth']['meta']['image_size']

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "split": split,
        "image_id": image_id,
        "width" : size['width'],
        "height": size["height"],
        "seconds": "",
        "n_texts": "",
        "status": "",
        "error": "",
    }

    start = time.perf_counter()
    try:
        result = ocr.predict(str(image_path))
        seconds = time.perf_counter() - start

        if not result:
            raise RuntimeError("[INFO] OCR Result is empty.")

        result[0].save_to_json(str(CACHE_DIR / split))

        saved = json.loads(cache_path(split, image_id).read_text(encoding="utf-8"))
        row.update(
            seconds = f"{seconds:.2f}",
            n_texts = len(saved['rec_texts']),
            status = "ok"
        )

    except Exception as exc:
        row.update(
            seconds=f"{time.perf_counter() - start:.2f}", 
            status="error",
            error=f"{type(exc).__name__}: {exc}"
        )
    append_log(row)
    return row

def main() -> None:
    args = parse_args()

    # Gather all of the jobs
    jobs = []
    for split in args.splits:
        # extract jsonl (dev/test) n return json
        records = load_records(split)[: args.limit]
        # create the cache directory for each split (dev/test)
        (CACHE_DIR / split).mkdir(parents=True, exist_ok=True)
        # in a record, there is split (dev/test) and record (a dictionary contains image id, file, and GT)
        # example: ("dev",  {"image_id": 0, "image_file": "images/dev/0000.png", "ground_truth": {...}})
        jobs += [(split, record) for record in records]

    # Remove the jobs that ALREADY have cache
    todo = [(split, record) for split, record in jobs if not is_valid_cache(cache_path(split, record['image_id']))]
    print(f"[INFO] Total Image: {len(jobs)} | Total Cached Image: {len(jobs) - len(todo)} "
          f"| Total Unprocessed Image: {len(todo)}")
    if not todo:
        print("[INFO] All image has been cached.")
        return

    # load model object one time
    start = time.perf_counter()
    ocr = PaddleOCR(
        use_doc_orientation_classify = False,
        use_doc_unwarping = False,
        use_textline_orientation = False,
    )
    print(f"[INFO] Loading model: {time.perf_counter() - start:.2f} s")

    # Process image OCR on per one
    ok_seconds = []
    n_error = 0
    for i, (split, record) in enumerate(todo, start=1):
        row = run_one(ocr, split, record)

        if row["status"] == "ok":
            ok_seconds.append(float(row["seconds"]))
        else:
            n_error += 1

        avg = sum(ok_seconds) / len(ok_seconds) if ok_seconds else 0.0
        eta_min = avg * (len(todo) - i) / 60

        print(f"[{i:>3}/{len(todo)}] {split:<4} {record['image_id']:04d} | "
              f"{row['seconds']:>6} s | text: {str(row['n_texts']):>3} | {row['status']:<5} | "
              f"eta last ~{eta_min:.0f} minutes"
              + (f" | {row['error']}" if row["error"] else ""))

    # print summary
    print(f"\n[INFO] All process finished. Success: {len(ok_seconds)} | Failed: {n_error}")
    if ok_seconds:
        print(f"[INFO] Mean: {sum(ok_seconds) / len(ok_seconds):.2f} s/img "
              f"| min {min(ok_seconds):.2f} s | max {max(ok_seconds):.2f} s")
    print(f"[INFO] Cache : {CACHE_DIR}")
    print(f"[INFO] Log   : {LOG_PATH}")

if __name__ == "__main__":
    main()