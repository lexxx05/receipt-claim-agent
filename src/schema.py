from pydantic import BaseModel, Field

class SubItem(BaseModel):
    name: str = Field(
        min_length=1, # min 1 character
        description="Name of the option or modifier printed under its parent item (e.g. 'Less Ice', 'Top Oreo').",
    )
    qty: float | None = Field(
        default=None,
        gt=0, # greater than 0
        description="Quantity of the sub-item if printed; null if not printed.",
    )
    price: int | None = Field(
        default=None,
        ge=0, # greater equal to 0
        description="Price printed on the sub-item line in whole rupiah; null if not printed.",
    )

class Item(BaseModel):
    name: str = Field(
        min_length=1,
        description="Item name EXACTLY as printed. A discount printed as its own line (e.g. 'Discount BCA 15%') is also an item.",
    )
    qty: float | None = Field(
        default=None,
        gt=0,
        description="Quantity as a number (e.g. '2 x', '3X', '1Prs' -> 2, 3, 1); Null if the receipt prints no quantity. NEVER guess",
    )
    unit_price: int | None = Field(
        default=None,
        ge=0,
        description="Price per unit in whole rupiah (e.g. '@12.000' -> 12000); null if not printed.",
    )
    price: int | None = Field(
        default=None,
        description="Total price of the item line in whole rupiah, before any item discount. Negative ONLY for a discount line.",
    )
    discount: int | None = Field(
        default=None,
        le=0, # less than or equal to (<=0) -> discount = negative
        description="Discount applied to this item as a negative number in whole rupiah; null if none.",
    )
    sub_items: list[SubItem] = Field(
        default=[],
        description="Options or modifiers printed under this item; empty list if none.",
    )

class Receipt(BaseModel):
    items: list[Item] = Field(
        min_length=1, # min 1 Item object
        description="All purchased items in printed order, excluding sub-items and payment lines.",
    )
    subtotal: int | None = Field(
        default=None,
        ge=0,
        description="Subtotal as printed in whole rupiah; null if not printed.",
    )
    service: int | None = Field(
        default=None,
        ge=0,
        description="Service charge in whole rupiah; null if not printed.",
    )
    tax: int | None = Field(
        default=None,
        ge=0,
        description="Tax amount (e.g. PB1, PPN, VAT) in whole rupiah; null if not printed.",
    )
    discount: int | None = Field(
        default=None,
        le=0, 
        description="Receipt-level discount as a negative number in whole rupiah; null if none.",
    )
    total: int | None = Field(
        default=None,
        ge=0,
        description="Final total to pay in whole rupiah, not the cash paid or change; null if not printed.",
    )