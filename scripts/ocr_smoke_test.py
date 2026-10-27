from paddleocr import PaddleOCR
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_PATH = PROJECT_ROOT / "data" / "samples" / "image.jpg"
OUTPUT_DIR = PROJECT_ROOT / "output" / "smoke_test"

if not IMAGE_PATH.is_file():
    raise SystemExit(f"[ERROR] Gambar tidak ditemukan: {IMAGE_PATH}")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

start = time.perf_counter()
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
load_seconds = time.perf_counter() - start

start = time.perf_counter()
result = ocr.predict(str(IMAGE_PATH))
predict_seconds = time.perf_counter() - start

print(f"[INFO] OCR Result type: {type(result)}\n[INFO] OCR Result Lenght: {len(result)}\n")


for res in result:
    res.print()
    res.save_to_img(OUTPUT_DIR)
    res.save_to_json(OUTPUT_DIR)

print(f"[INFO] Muat model : {load_seconds:.2f} detik")
print(f"[INFO] Predict    : {predict_seconds:.2f} detik")