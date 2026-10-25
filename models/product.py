"""Values copied from the catalog before navigating to a product page."""

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductSnapshot:
    product_id: int
    name: str
    price: Decimal


def parse_price(text: str) -> Decimal:
    match = re.fullmatch(r"Rs\.\s*(\d+(?:\.\d+)?)", text.strip())
    assert match, f"Cannot read product price: {text!r}"
    return Decimal(match.group(1))
