# Receipt Claim Agent
 
An agent that checks expense-reimbursement claims from receipt photos: it reads the receipt with OCR, turns the text into structured data with an LLM, validates the numbers, and decides **approve / reject / review** with a reason and the policy clause it relied on.

## Pipeline
 
```
receipt photo
   │  Stage 1  OCR (PaddleOCR, CPU)                    
   ▼
text boxes + confidence scores
   │  Stage 2  Preprocessing (filter token + line grouping)  
   ▼
receipt text, one printed line per row
   │  Stage 3  LLM parser (Gemini, structured output) 
   ▼
structured receipt (Pydantic schema)
   │  Stage 4  Validator (schema, arithmetic, numbers must exist in OCR text)
   ▼
   │  Stage 5  Claim agent (Strands) + expense policy
   ▼
decision · reason · policy clause
```

## Dataset
 
[CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2): photos of Indonesian receipts with word-level boxes and parsed labels.
 
| Split | Receipts | Used for |
|---|---|---|
| `validation` → **dev** | 100 | All analysis, parameter choices, prompt tuning |
| `test` → **test** | 100 | Held out; opened once for the final numbers |
 
The data understanding (field glossary, number formats, arithmetic patterns, design decisions) is in [`data/README.md`](data/README.md).
 
---

## Stage 1: OCR

**Engine:** PaddleOCR 3.7 with the default PP-OCRv6 medium detection and recognition models, running on CPU. Document orientation, unwarping and text-line orientation are switched off for this baseline.

**Batch run:** `scripts/ocr_all.py` runs OCR on all 200 dev and test images once and caches the full PaddleOCR output (text, score, bounding box) per image, so later stages never re-run OCR. The run is resumable (a cached image is skipped; a half-written cache file is redone) and logs per-image latency.

**Latency on CPU (dev split, 100 images):** median **23.1 s** per image; the 11 images above 8 megapixels have a median of **82 s**. The median is reported because a few images in one stretch of the run took several minutes, including a small 1108×1478 image, which points to machine load rather than image size.

---

## Stage 2: Preprocessing

OCR returns loose text pieces with boxes, in no reading order. In the other side, the parser needs the receipt as it is printed: one row per line, label and price together.

```
OCR output (dev 0000, simplified)        After preprocessing
-------------------------------          --------------------------
("Jmunn", 0.44, [432,163,581,225])        1 REAL GANACHE | 16,500
("1 REAL GANACHE", 0.99, [...])           1 EGG TART | 13,000
("16,500", 0.99, [...])                   1 PIZZA TOAST | 16,000
("1 EGG TART", 0.99, [...])               TOTAL | 45,500
...                                       CASH | 50,000
                                          CHANGE | 4,500
```

Both parameters below were chosen from the dev split by comparing against CORD's ground truth, not guessed.

### Step 1 - Drop low-confidence text
 
A text piece is *labeled* if its box contains the centre of a ground-truth word; unlabeled pieces are mostly garbage from blurred store headers, plus some real but unlabeled text. Dev split: 1,610 OCR pieces, 1,408 labeled, 202 unlabeled.
 
| Score threshold | Labeled pieces dropped | Unlabeled pieces dropped |
|---|---|---|
| 0.3 | 1 (0.1%) | 36 (17.8%) |
| **0.5 (chosen)** | **2 (0.1%)** | **96 (47.5%)** |
| 0.7 | 5 (0.4%) | 138 (68.3%) |
| 0.9 | 21 (1.5%) | 156 (77.2%) |
 
Many labeled pieces with low scores are short quantities (`1`, `2`, `x1`), which OCR reads least reliably. A higher threshold removes more garbage but starts deleting real quantities, so 0.5 is the cut-off.

### Step 2 - Group text into lines
 
Two pieces are on the same line when their **vertical overlap** is at least a share of the shorter box's height; each piece is compared with the average top and bottom of the lines built so far. Within a line, pieces are ordered left to right and joined with ` | ` so the parser can see where the name ends and the price begins.
 
Grouping is scored against CORD's line ids (`row_id`): for every pair of labeled pieces in a receipt, does the pipeline make the same "same line / different line" call as the ground truth? A receipt counts as *perfect* only if every pair agrees.
 
| Rule | Pair agreement | Perfect receipts |
|---|---|---|
| Vertical overlap ≥ 0.3 | 97.37% | 55 / 100 |
| **Vertical overlap ≥ 0.5 (chosen)** | **99.05%** | **79 / 100** |
| Vertical overlap ≥ 0.7 | 98.85% | 70 / 100 |
| Centre gap < 0.3 × median height | 98.67% | 63 / 100 |
| Centre gap < 0.5 × median height | 97.66% | 72 / 100 |
 
The pair score is high because most pairs are easy "different line" cases; *perfect receipts* is the stricter number. 21 receipts still have at least one grouping error.
 
### Limitations
 
- Line **order** is not scored, only grouping; order is checked visually with `--show`.
- Tilted receipts are not deskewed yet; whether this hurts the parser will be measured in Stage 3 before adding a fix.
- All numbers are from the dev split.

---

## Reproduce
 
```bash
# environment: Python 3.11 (conda); install paddlepaddle (CPU) from the official index first
pip install -r requirements.txt
 
python scripts/prepare_cord.py              # CORD parquet -> PNG + ground-truth JSONL
python scripts/ocr_all.py                   # OCR all images once, cache results
python -m scripts.check_preprocess          # grouping score on dev
python -m scripts.check_preprocess --show 0 # preprocessed text for dev 0000
```
 
## License and citation
 
CORD is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) by NAVER Clova ([clovaai/cord](https://github.com/clovaai/cord)).