"""Values copied from the catalog before navigating to a product page."""

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductSnapshot:
    product_id: int
    name: str
    price: Decimal


def select_search_products(products):
    """Select a name query and an unrelated control from the current catalog.

    Automation Exercise test case 9 searches by product name. Disjoint words
    keep the control unrelated even if search matches individual query words.
    """
    for selected in products:
        words = re.findall(r"\w+", selected.name.casefold())
        if not words:
            continue
        for control in products:
            name = control.name.casefold()
            if name.strip() and all(word not in name for word in words):
                return selected, control
    raise AssertionError("Catalog has no name query with an unrelated control product")


def parse_price(text: str) -> Decimal:
    match = re.fullmatch(r"Rs\.\s*(\d+(?:\.\d+)?)", text.strip())
    assert match, f"Cannot read product price: {text!r}"
    return Decimal(match.group(1))
