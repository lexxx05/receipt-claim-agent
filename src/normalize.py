"""
normalize.py aims top normalize the raw value CORD to a `Receipt` schema.

- parse_amoount : price string (int or none)
- parse_qty     : quantity string (float or none)
- gt_to_receipt : gt_parse CORD -> Receipt Object (validated)
"""

import re
from decimal import Decimal, ROUND_HALF_UP

from src.schema import Item, Receipt, SubItem

# Regex Pattern
_SPACED_THOUSANDS = re.compile(r"(?<=\d) (?=\d{3}(?!\d))") # before space MUST have digit, space between digit, followed by exactly 3 digits and there is no 4th digit
_AMOUNT_TOKEN = re.compile(r"\d[\d.,]*") # the first number start with digit, followed by digit / . / ,
_DECIMAL_TAIL = re.compile(r"[.,]\d{2}$") # . or , and then followed by exactly 2 digits
_QTY_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[.,]\d+") # optional integer + decimal, or decimal that started with .

def parse_amount(text) -> int | None:
    """
    normalize the price string -> int rupiah
    """
    if text is None:
        return None
    s = str(text).strip() # remove space before n after string
    if not s:
        return None

    s = _SPACED_THOUSANDS.sub("", s) # merge price separated by space: 154 000 -> 154000

    match = _AMOUNT_TOKEN.search(s) # look for first digit. ex: "-Rp 34,363" -> match "34,363"
    if match is None:
        return None
    token = match.group(0).rstrip(".,") # grab only the digit, remove . or , at the end. ex: 60.000) -> token 60.000

    before = s[: match.start()] # text before digit. ex: "-Rp 34,363" -> "-Rp "
    after = s[match.end():] # text after digit. ex: "60.000)"   -> ")"
    negative = "-" in before or "(" in before or after.startswith(")") # flag for the discount format
    # negative example: "-9,545" (there is a "-"), "-Rp 34,363" (there is a "-"), "60.000)" (followed by ")"), "(5.000)" (there is a "(")

    if _DECIMAL_TAIL.search(token): # if there is 2 last decimal digit at the end appears. ex: "5272.73", "58000.00"
        whole = re.sub(r"\D", "", token[:-3]) or "0" # extract the whole digit. ex: "5272.73" -> "5272"
        value = Decimal(whole) + Decimal(token[-2:]) / 100 # 5272 + last 2 char (73 / 100) -> 5272 + 0.73 = 5272.73
    else:
        value = Decimal(re.sub(r"\D", "", token)) # ex: "16,500" -> "16500" | "24.000" -> "24000" | "6500" -> "6500"

    rupiah = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) # round to rupiah, eg. 5272.73 -> 5273 | 58000.00 -> 58000

    return -rupiah if negative else rupiah

def parse_qty(text) -> float | None:
    """
    normalize the quantity string -> float
    """
    if text is None:
        return None
    match = _QTY_TOKEN.search(str(text)) # search for the first number. eg: "1Prs" -> "1" | "*2" -> "2"
    if match is None:
        return None
    return float(match.group(0).replace(",",".")) # make float radable, eg. "1,5" -> 1.5

def as_list(value) -> list:
    """
    ensure that the object is already in list data structure
    """
    if value is None:
        return []
    return value if isinstance(value, list) else [value] # return in list for whatever the data structure type

def _text(value) -> str:
    """
    merge the component between list
    """
    if isinstance(value, list): # name is placed on list. eg. ['-', 'Gyro Platter Regular']
        value = " ".join(str(v) for v in value) # combined using space -> "- Gyro Platter Regular"
    return str(value).strip() if value is not None else ""

def gt_to_receipt(gt_parse: dict) -> Receipt:
    """
    convert the groundtruth to a Receipt pydantic class
    """
    items = []
    for raw in as_list(gt_parse.get("menu")): # raw is ONE CORD ITEM. eg. 0008: {"nm": "TALAM UNGU", "unitprice": "@6500", "cnt": "3X", discountprice": "-7,800", "price": "19,500"}
        sub_items = [
            SubItem(
                name = _text(sub.get("nm")),
                qty = parse_qty(sub.get("cnt")),
                price = parse_amount(sub.get("price"))
            )
            for sub in as_list(raw.get("sub")) # sub can be either dict or list -> convert to list
            if _text(sub.get("nm")) # if sub item has name
        ]

        items.append(
            Item(
                name = _text(raw.get("nm")), # "TALAM UNGU"
                qty = parse_qty(raw.get("cnt")), # "3X"      -> 3.0
                unit_price = parse_amount(raw.get("unitprice")), # "@6500"   -> 6500
                price = parse_amount(raw.get("price")), # "19,500"  -> 19500
                discount = parse_amount(raw.get("discountprice")), # "-7,800"  -> -7800
                sub_items = sub_items, # []
            ) # item will be validated directly on schema, ex. discount = 7800 (+) will validation error because le = 0
        ) 

    sub_total = gt_parse.get("sub_total") or {}
    total = gt_parse.get('total') or {}

    return Receipt(
        items=items,
        subtotal=parse_amount(sub_total.get("subtotal_price")),  # 0008: "11,700" -> 11700
        service=parse_amount(sub_total.get("service_price")),    # 0021: "Rp 9,736" -> 9736
        tax=parse_amount(sub_total.get("tax_price")),            # 0077: "Rp 5272.73" -> 5273
        discount=parse_amount(sub_total.get("discount_price")),  # 0007: "-9,545" -> -9545
        total=parse_amount(total.get("total_price")),            # 0008: "11,700" -> 11700
    )

# the other like cash price, change price, credit card, etc will not be read -> automatically deleted