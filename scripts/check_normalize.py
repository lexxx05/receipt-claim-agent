"""
check_normalize.py, aims to:
1. check the normalization function based on 27 test case dataset evaluation, 
to maken sure that the normalization result is already match
2. check normalization function to all dev jsonl only to makesure
that it will be not occuring pydantic error (schema match), not checking the result

how to run:
python -m scripts.check_normalize

result:
[INFO] PASSED: 27/27 TEST CASES
[INFO] 100 / 100 SUCCESS converted to Receipt Pydantic Class.
[INFO] all testing passed.
"""

import json  
from pathlib import Path

from pydantic import ValidationError # error pydantic if data is not match to schema

from src.normalize import gt_to_receipt, parse_amount, parse_qty  # function need to be evaluated


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_JSONL = PROJECT_ROOT / "data" / "CORD" / "gt" / "dev.jsonl"  # GT result from prepare_cord.py

# EXAMPLE of test cases (input, expected)
AMOUNT_CASES = [
    ("16,500", 16500),          
    ("24.000", 24000),         
    ("Rp 36.000", 36000),      
    ("@ 12.000", 12000),        
    ("@6500", 6500),           
    ("-9,545", -9545),         
    ("-Rp 34,363", -34363),     
    ("60.000)", -60000),        
    (":9,000", 9000),           
    ("154 000", 154000),        
    ("Rp 58000.00", 58000),     
    ("Rp 5272.73", 5273),     
    ("0", 0),                   
    ("Discount(0%)", 0),       
    (None, None),             
    ("", None),                 
]
QTY_CASES = [
    ("1", 1.0), ("3X", 3.0), ("2 x", 2.0), ("x2", 2.0), ("*2", 2.0),  
    ("1Prs", 1.0), ("1Gls", 1.0),                                     
    ("1.00", 1.0), (".5", 0.5), ("170", 170.0),                    
    (None, None),                                               
]

# small evaluation function test cases
def check_cases() -> int:
    failed = 0
    for func, cases in ((parse_amount, AMOUNT_CASES), (parse_qty, QTY_CASES)):
        # 1st loop evaluate parse amount with amount cases - 2nd loop for quantity
        for text, expected in cases:
            got = func(text) # call the function (parse_amount or parse__qty)
            if got != expected:
                failed += 1
                print(f"[FAIL] {func.__name__}({text!r}) = {got!r}, expected {expected!r}")
        total = len(AMOUNT_CASES) + len(QTY_CASES)
        print(f"[INFO] PASSED: {total - failed}/{total} TEST CASES")
        return failed

# Convert ALL DEV GROUND TRUTH into the receipt pydantic
def check_dev() -> int:
    failed = 0
    count = 0
    with DEV_JSONL.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            count += 1
            try:
                gt_to_receipt(record["ground_truth"]["gt_parse"])
            except ValidationError as exc:
                failed += 1
                print(f"[FAIL] dev {record['image_id']:04d}")
                for err in exc.errors():
                    print(f"       {'.'.join(map(str, err['loc']))}: {err['msg']} (input={err['input']!r})")

    print(f"[INFO] {count - failed} / {count} SUCCESS converted to Receipt Pydantic Class.\n")

    return failed

def main() -> None:
    failed = check_cases() + check_dev()                 
    if failed:                                           
        raise SystemExit(f"[ERROR] {failed} testing is failed")
    print("[INFO] all testing passed")

if __name__ == "__main__":  
    main()