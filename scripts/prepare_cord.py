import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORD_DIR = PROJECT_ROOT / "data" / "CORD"

SPLITS = {
    "dev": "validation-00000-of-00001-cc3c5779fe22e8ca.parquet",
    "test": "test-00000-of-00001-9c204eb3f4e11791.parquet",
}

# split itu dev atau test, parquet_name itu nama testnya, sesuai dict SPLITS
def prepare_split(split: str, parquet_name: str) -> None:
    parquet_path = CORD_DIR / parquet_name
    if not parquet_path.is_file():
        raise SystemExit(f"[ERROR] Parquet tidak ditemukan: {parquet_path}")

    image_dir = CORD_DIR / "images" / split
    gt_dir = CORD_DIR / "gt"
    image_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(parquet_path)
    jsonl_path = gt_dir / f"{split}.jsonl"
    seen_ids = set()

    # tulis gambar dan satu baris jsonl PER STRUK dari file parquet ori
    with jsonl_path.open("w", encoding="utf-8") as f:
        # iterationnya per row, lebih cepet dari iterrows, bisa dibaca row.image dan row.ground_truth (nama kolom)
        for row in df.itertuples(index=False):
            gt = json.loads(row.ground_truth)
            image_id = gt['meta']['image_id']

            # ini pengaman biar id ga double dan silent treatment
            if image_id in seen_ids:
                raise SystemExit(f"[ERROR] image_id ganda di split {split}: {image_id}")
            seen_ids.add(image_id)

            # write EACH image path dari image id dan isinya
            image_path = image_dir / f"{image_id:04d}.png"
            image_path.write_bytes(row.image['bytes'])

            # add new record di jsonl yg isinya image id, path filenya, dan ground truthnya
            record = {
                "image_id": image_id,
                "image_file": image_path.relative_to(CORD_DIR).as_posix(),
                "ground_truth": gt,
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    n_images = len(list(image_dir.glob("*.png")))
    print(f"[INFO] {split:<4} | baris parquet: {len(df)} | PNG: {n_images} | GT: {jsonl_path.name}")
    if n_images != len(df):
        print(f"[WARN] Jumlah PNG ({n_images}) beda dengan baris parquet ({len(df)})")

def main() -> None:
    for split, parquet_name in SPLITS.items():
        prepare_split(split, parquet_name)

if __name__ == "__main__":
    main()

