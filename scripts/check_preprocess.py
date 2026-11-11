import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from src.preprocess import build_text, filter_tokens, group_lines, load_ocr_tokens

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_JSONL = PROJECT_ROOT / "data" / "CORD" / "gt" / "dev.jsonl"
OCR_DIR = PROJECT_ROOT / "data" / "ocr_cache" / "dev"

####################################################
# Extract centroid setiap kata GT + Nomor Barisnya #
####################################################
def gt_word_words(ground_truth: dict) -> list[tuple[float, float, int]]:
    """
    ekstrak 4 sudut bounding box kata ground truth
    return centroid x, centroid y, dan nomor baris versi GT
    """
    words = []
    for valid_line in ground_truth['valid_line']:
        for word in valid_line['words']:
            q = word['quad']
            # centroid horizontal (rata rata x)
            cx = (q['x1'] + q['x2'] + q['x3'] + q['x4']) / 4
            # centroid vertikal (rata rata y)
            cy = (q["y1"] + q["y2"] + q["y3"] + q["y4"]) / 4
            words.append((cx, cy, word['row_id']))
    return words

##############################
# Baris GT untuk 1 Token OCR #
##############################
def token_row(token, words) -> int | None:
    x1, y1, x2, y2 = token.box
    rows = [row for cx, cy, row in words if x1 <= cx <= x2 and y1 <= cy <= y2]
    if not rows:
        return None
    return Counter(rows).most_common(1)[0][0]

########################################################
# Evaluasi pengelompokan baris OCR di seluruh data dev #
########################################################
def evaluate() -> None:
    # agree     : jumlah pasangan yang keputusannya sama kayak GT
    # total     : jumlah semua pasangan yang dinilai
    # perfect   : jumlah struk yang semua pasangannya benar
    # receipts  : jumlah struk yang diproses (100)
    agree = total = perfect = receipts = 0
    with DEV_JSONL.open(encoding='utf-8') as f:
        for line in f: # per satu observasi struk
            # --- Ground truth
            record = json.loads(line)
            image_id = record['image_id']
            words = gt_word_words(record['ground_truth']) # ambil kata yang di GT dalam 1 row berdasarkan data row_idnya
            
            # --- Hasil padel OCR dalam bentuk token yang udah di filter
            tokens = filter_tokens(load_ocr_tokens(OCR_DIR / f"{image_id:04d}_res.json"))

            # kelompokin token paddle OCR jadi baris (koordinat x y)
            lines = group_lines(tokens)

            # disini kita akan bandingin pengelompokan row_id hasil preprocess kita, dengan data row_id yg udah ada di GT
            # contoh:
            # Token             Pengelompokan baris kita (pred)     row_id GT
            # 1 REAL GANACHE    0                                   2068522     (cocok)
            # 16,500            0                                   2068522     (cocok)
            # 1 EGG TART        1                                   2068523     (cocok)
            # 13,000            1                                   2068523     (cocok)
            pred, true = [], [] # pred = nomor baris kita, true = row_id GT
            for line_no, line_tokens in enumerate(lines):
                for token in line_tokens:
                    row = token_row(token, words)
                    if row is not None:
                        pred.append(line_no)
                        true.append(row)

            receipt_ok = True
            for a, b in combinations(range(len(pred)), 2): 
                # bandingin tiap pasangan token di struk ini yang menghasilkan semua pasangan tanpa pengulangan: n x (n-1) / 2, 
                # misal struk 0000 punya 12 token yang dinilai, maka 12 x 11/2 = 66
                same_pred = pred[a] == pred[b] # apakah prediksi kita sebaris dari 2 token ini
                same_true = true[a] == true[b] # apakah GT sebaris dari 2 token ini
                # gabisa row id = pengelompokan kita karna beda nomor seri: MAKA kita bilang cocok kalo preprocess kita bilang hal yang SAMA kayak GT (bukan benar atau salah)
                total += 1
                if same_pred == same_true:
                    agree += 1
                else:
                    receipt_ok = False # 1 pasangan salah -> struk ga sempurna
            
            perfect += receipt_ok
            receipts += 1

    print(f"[INFO] Akurasi pasangan     : {agree / total:.2%} ({agree}/{total} pasangan)")
    print(f"[INFO] Struk 100% benar     : {perfect}/{receipts}")

    # contoh pasangan: ("1 REAL GANACHE", "16,500") -> kita: sebaris, GT: sebaris -> agree
    #                  ("16,500", "1 EGG TART")     -> kita: beda baris, GT: beda baris -> agree

############################
# Cetak teks untuk 1 STRUK #
############################
def show(image_id: int) -> None:
    tokens = load_ocr_tokens(OCR_DIR / f"{image_id:04d}_res.json")
    print(f"[INFO] dev {image_id:04d} | OCR tokens: {len(tokens)} | after filter: {len(filter_tokens(tokens))}")
    print(build_text(tokens))

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", type=int, help="number of image id that you want to display")  # Contoh: --show 8
    args = parser.parse_args()
    if args.show is not None:
        show(args.show)
    else:
        evaluate()

if __name__ == "__main__":
    main()