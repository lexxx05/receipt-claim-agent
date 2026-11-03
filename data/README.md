# Data Understanding: CORD v2

## 0. How to prepare the data

1. Download the two parquet files (`validation` and `test` set) from [naver-clova-ix/cord-v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2) into `data/CORD/`.
2. `python scripts/prepare_cord.py` → `data/CORD/images/{dev,test}/` and `data/CORD/gt/{dev,test}.jsonl`
3. `python scripts/ocr_all.py` → `data/ocr_cache/{dev,test}/*_res.json` and `data/ocr_cache/ocr_log.csv`

Everything in `data/` except this file is **ignored by Git**.

## 1. Dataset summary

| Item | Value |
|---|---|
| Source | [naver-clova-ix/cord-v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2) (Hugging Face) |
| Splits used | `validation` → **dev** (100 receipts), `test` → **test** (100 receipts) |
| Format | PNG + `ground_truth` (JSON: `gt_parse`, `valid_line`, `meta`) |
| Resolution (dev) | 432×648 to 2376×4224 (long side 648–4224 px, ~6.5×) |
| Store / date labels | None (store name and address are blurred by CORD) |

All analysis below uses the **dev split only**. The test split is held out and is opened only once, for the final evaluation.

### 1.1 Ground-truth structure

Each receipt's `ground_truth` has three parts used in this project:

| Key | Content | Used for |
|---|---|---|
| `gt_parse` | Nested JSON with the parsed values (`menu`, `sub_total`, `total`) | Parser target and end-to-end evaluation |
| `valid_line` | Labeled text lines; each word has its text and a 4-point box (`quad`) | OCR-only evaluation (layer A) and parser-only evaluation (layer B) |
| `meta` | `image_id`, `split`, `image_size` | File naming, resolution analysis |

`menu` is a **list** when a receipt has several items and a **dict** when it has one (dev: 54 list, 46 dict). Sub-items are nested as `menu[].sub`, which can also be a list or a dict.

### 1.2 Field glossary

Definitions follow the official [CORD class definition](https://github.com/clovaai/cord). Counts are occurrences in `gt_parse` of the **dev split**.

**Naming note:** the Hugging Face version uses `sub_total.*` and nests sub-items as `menu[].sub[].*`; the official documentation writes `subtotal.*` and `menu.sub_nm`, `menu.sub_cnt`, `menu.sub_price`.

| Field (HF `gt_parse`) | Meaning | dev |
|---|---|---|
| `menu[].nm` | Item name | 221 |
| `menu[].cnt` | Item quantity | 210 |
| `menu[].unitprice` | Unit price | 50 |
| `menu[].price` | Total price of the item line | 220 |
| `menu[].discountprice` | Discount on the item | 4 |
| `menu[].num` | Item ID / code | 4 |
| `menu[].vatyn` | Whether the price includes tax | 1 |
| `menu[].sub[].nm` | Sub-item name (option, modifier) | 49 |
| `menu[].sub[].cnt` | Sub-item quantity | 32 |
| `menu[].sub[].price` | Sub-item total price | 14 |
| `sub_total.subtotal_price` | Subtotal | 67 |
| `sub_total.discount_price` | Total discount | 6 |
| `sub_total.service_price` | Service charge | 13 |
| `sub_total.tax_price` | Tax amount | 47 |
| `sub_total.etc` | Other subtotal-level info | 1 |
| `total.total_price` | Total price | 98 |
| `total.total_etc` | Other total-level info | 4 |
| `total.cashprice` | Amount paid in cash | 64 |
| `total.changeprice` | Change given | 64 |
| `total.creditcardprice` | Amount paid by credit/debit card | 14 |
| `total.emoneyprice` | Amount paid by e-money / points | 4 |
| `total.menutype_cnt` | Number of distinct items | 3 |
| `total.menuqty_cnt` | Total item quantity | 26 |

Labels in the official definition that do not appear in dev: `menu.itemsubtotal`, `menu.etc`, `menu.sub_unitprice`, `subtotal.othersvc_price`, `void_menu.*`.

## 2. Observation method

- Tool: `scripts/show_receipt_gt.py` (GT + image with GT box overlay).
- Sample: receipts 0–5 and 14 (sequential), then 9 receipts chosen **on purpose** to cover variations not yet seen: discount (7, 8), service charge (21, 25), decimals (39, 77, 90), sub-items (22, 36).
- For each receipt: compare the image with `gt_parse`; check the arithmetic by hand. 
- Scope: properties of the data only. OCR output is analysed separately in the OCR evaluation.

## 3. Observation table

Legend: ✓ holds · ✗ does not hold · – cannot be checked (field missing)

| id | Size | Items | Number format | qty×unit=price | Σprice=subtotal | Σprice=total | Totals formula holds | Sub-items | Image quality | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 0000 | 864×1296 | 3 | `16,500` | – | – | ✓ | – | ✗ | clear | qty left of name |
| 0001 | 1108×1478 | 1 | `23.000` | – | – | ✓ | – | ✗ | small receipt in frame | qty right of name |
| 0002 | 418×740 | 1 | `20,000` | ✓ | ✗ | ✓ | off by 1 | ✗ | folded, low resolution | prices include tax (`vatyn`); subtotal is net |
| 0003 | 2304×4096 | 1 | `@28,000`, `1X` | ✓ | ✓ | ✓ | ✓ | name only | small receipt, tilted | tax `"0"` |
| 0004 | 576×864 | 1 | `41,000` | – | ✓ | ✓ | ✓ (no tax) | name + qty + price 0 | crumpled | GT `changeprice: ":9,000"` (label noise) |
| 0005 | 960×1280 | 1 | `8,000`, qty `1.00` | – | ✗ | ✓ | ✓ | ✗ | faded | prices include tax (NETT AMT) |
| 0007 | 576×864 | 1 | `63,636`, `-9,545` | – | ✓ (before discount) | ✗ | ✓ subtotal − discount + tax | ✗ | faded, watermark over digits | discount at item **and** subtotal level; tax computed after discount |
| 0008 | 576×864 | 2 | `19,500`, `@6500`, `3X`, `-7,800` | ✓ | ✗ | ✗ | ✓ (no tax) | ✗ | clear | item-level discount; `price` is **before** discount, subtotal and total are **after** it (19,500 − 7,800 = 11,700); `menuqty_cnt "4.00xITEMs"` |
| 0014 | 605×1280 | 2 | `Rp 36.000`, `@ 12.000`, `2 x` | ✓ | ✓ | ✗ | ✓ | ✗ | clear | qty on the line below the name |
| 0021 | 864×1296 | 4 | `Rp 29,090`, `-Rp 34,363` | – | ✓ (incl. discount line) | ✗ | ✓ subtotal + service + tax | ✗ | clear, glare | discount as a **negative menu line**; service 5%; tax 10% of subtotal + service |
| 0025 | 2304×4096 | 7 | `33,000`, `1Prs`, `1Gls` | – | ✓ | ✗ | ✓ subtotal + service + tax | ✗ | faded print, stamp | service 5%; tax 10% of subtotal + service; GT `Mie Trsi Kgkung` vs printed `Mie Kgkung Trsi` |
| 0039 | 2304×4096 | 5 | `26,000` | – | ✓ | ✗ | ✓ | ✗ | clear, stamp over items | **no qty** on receipt or in GT; `menuqty_cnt "5.00"` is the only decimal |
| 0077 | 864×1296 | 1 | `Rp 58000.00`, `Rp 5272.73`, `*2` | – | ✓ | ✓ | ✓ total = subtotal (tax included) | name only | blurry | only real cents value in dev; dot used as decimal separator |
| 0090 | 576×864 | 1 | `35000.00`, `70000.00` | ✓ | – | ✓ | – | ✗ | shadow, watermark | `total_etc` = "OFFLINE PROMO" payment line |
| 0022 | 576×864 | 1 | `280,000` | – | ✓ | ✗ | ✓ subtotal + tax | name + qty, no price | faded | GT sub-item qty `".5"` (unusual value) |
| 0036 | 864×1296 | 1 | `17,272` | – | ✓ | ✗ | ✓ subtotal + tax | name + price 0 | faded, watermark | repeated sub-item name ("Top Oreo" ×2) is valid |

## 4. Findings

### 4.1 Number format
- Dots **and** commas are both used as thousands separators (`16,500` / `24.000`).
- Some receipts use a dot as the **decimal** separator with no thousands separator (`58000.00`, `35000.00`; 0077, 0090).
- Rule that fits every observed **money** value: if the last separator is followed by exactly **2** digits it is a decimal point; if followed by **3** digits it is a thousands separator.
- Real cents appear once in the whole dev split (`5272.73`, a tax-included amount in 0077); all other decimals are `.00`.
- Prefixes/suffixes: `Rp`, `@`, `x`/`X`, `*`, `:` (label noise).
- Negative values use a leading `-` (`-9,545`, `-Rp 34,363`) or accounting parentheses: GT `"60.000)"` in 0055 must be negative, since 60,000 + 60,000 + (−60,000) = 60,000 = total.

### 4.2 Arithmetic
Two separate questions decide whether a receipt adds up. 

**Item level — what do item prices sum to?**
- Σprice = subtotal: tax and service are added on top (0003, 0004, 0007, 0014, 0021, 0022, 0025, 0036, 0039, 0077).
- Σprice = total: item prices already include tax, and the printed subtotal is the net amount (0002, 0005).
- Neither, unless item discounts are applied: 0008 (`price` before discount; subtotal and total after it).

**Receipt level — how is the total built?**
- total = subtotal + service + tax + discount (discount negative) holds for every receipt that has both subtotal and total (0002 off by 1 from rounding), **except 0077**.
- 0077: total = subtotal, because the subtotal itself already includes tax; the printed tax (`5272.73` = 58,000 × 10/110) is informational.

**Rates seen:** service 5% of subtotal; tax 10% of **subtotal + service** (0021, 0025); tax computed **after** discount (0007).

### 4.3 Discounts
Three representations in the GT:
- Item-level `discountprice`, with `price` before discount (0007, 0008).
- Receipt-level `sub_total.discount_price` (0007, alongside the item-level value).
- A separate menu line with a negative price (0021, "Discount BCA 15%").
- The meaning of `subtotal` is **not consistent**: before discount in 0007, after discount in 0008.
- The same printed layout is labeled differently: a discount printed on its own line is a separate negative item in 0021 but an item-level `discountprice` attached to the previous item in 0055. Item-level scores can differ even when totals match.

### 4.4 Item structure
- Qty position: left of the name (0000, 0002, 0003, 0004, 0021, 0025), right of the name (0001), on the line **above** the name (0008), on the line **below** the name (0005, 0014). 
- Qty forms: `1`, `3X`, `2 x`, `1Prs`, `1Gls`, `*2`, `1.00`; some receipts print **no qty** at all (0039).
- Sub-items have three shapes: name only (0003, 0077), name + qty (0022), name + price 0 (0004, 0036). Sub-item prices never add to the subtotal.

### 4.5 Image quality
- Resolution varies widely (dev long side 648–4224 px, ~6.5×).
- Common capture issues: folds and crumples (0002, 0004), faded print (0005, 0022, 0025, 0036), blur (0077), shadow (0090), small receipt in a large frame (0001, 0003).
- Watermarks and stamps overlap text and digits (0007, 0025, 0036, 0039, 0090).
- Store name and address are blurred by CORD for privacy.

### 4.6 Ground-truth limitations
- Unlabeled text (store, address, footer) has no GT box, so OCR precision cannot be measured.
- Minor label noise: `":9,000"` (0004), word order `Mie Trsi Kgkung` vs printed `Mie Kgkung Trsi` (0025).
- Unusual GT value: sub-item qty `".5"` (0022).
- One GT sub-item has no name (0086: `{"price": "26,000"}` under `LEMONADE22OZ`). The schema requires a sub-item name, so this sub-item is dropped when the GT is normalized and does not count in evaluation.


## 5. Design decisions

| # | Decision | Choice | Rationale | Evidence (receipt ids) |
|---|---|---|---|---|
| 1 | Evaluation fields | Items (name, qty, price), subtotal, service, tax, discount, total. `unitprice` is extracted for validation but not scored. Payment fields (cash, change, card, e-money) are excluded. | The totals formula needs service and discount; without them, correct receipts fail validation. Payment fields do not affect a reimbursement decision. | 0007, 0021 |
| 2 | Money type | `int` (rupiah, rounded) | Only one real cents value exists in the whole dev split, and it is an informational tax already included in the total. The validator uses a tolerance. | 0077 (only case), 0090 (`.00`) |
| 3 | Sub-items | Stored as `sub_items` inside the parent item; name required, qty and price optional; never added to sums | Prevents modifiers from being counted as items; three shapes observed. | 0003, 0004, 0022, 0036, 0077 |
| 4 | Qty | `float` or `None` | Some receipts print no qty, so the parser must not invent one; decimal qty exists. | 0039 (no qty), 0005 (`1.00`) |
| 5 | Discount | Follow the GT shape: item-level `discount`, receipt-level `discount`, and a discount line stays an item with a negative price | Direct comparison with GT, no extra conversion; the validator needs item-level discounts. | 0007, 0008, 0021 |

**Limitation from decision 2:** amounts with cents are rounded to whole rupiah (e.g. 0077 tax `5272.73` → 5273).

## 6. Implications for the pipeline

| Component | Implication |
|---|---|
| Normalization | Strip `Rp`, `@`, `x`/`X`, `*`, `:`; a leading `-` or surrounding/trailing parentheses mean negative; last separator + 2 digits = decimal, + 3 digits = thousands; qty `1.00` → 1 |
| Preprocessing | Group text into lines by y; filter low-score text; watermarks and stamps overlap digits on some receipts |
| Prompt | Cover 4 qty positions (left, right, above, below the name), missing qty, 3 discount forms, sub-items, and tax-included receipts; few-shot examples span these variants |
| Validator | (1) qty × unitprice ≈ price when both exist; (2) Σprice **or** Σ(price + item discount) ≈ subtotal **or** ≈ total; (3) total ≈ subtotal + service + tax + discount **or** total ≈ subtotal (tax included); small tolerance for rounding |
| Evaluation | Normalize GT with the same function as predictions; sub-item prices excluded from sums |