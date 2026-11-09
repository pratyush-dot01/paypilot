from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Union, Dict, Any

CENT = Decimal("0.01")

def to_decimal(val: Union[float, int, str, Decimal, None], default: str = "0.00") -> Decimal:
    """Safely convert a number or string to a Decimal with 2 decimal places."""
    if val is None:
        return Decimal(default).quantize(CENT, rounding=ROUND_HALF_UP)
    if isinstance(val, Decimal):
        return val.quantize(CENT, rounding=ROUND_HALF_UP)
    # Convert through string representation to prevent float precision artifacts
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)

def round_amount(val: Decimal) -> Decimal:
    """Round decimal to 2 decimal places using standard financial rounding (ROUND_HALF_UP)."""
    return val.quantize(CENT, rounding=ROUND_HALF_UP)

def calculate_item_total(quantity: Union[int, Decimal], unit_price: Union[float, int, str, Decimal]) -> Decimal:
    """Calculate the total for a single line item: quantity * unit_price."""
    qty = Decimal(str(quantity))
    price = to_decimal(unit_price)
    if qty < Decimal("0"):
        raise ValueError("Item quantity cannot be negative")
    if price < Decimal("0"):
        raise ValueError("Item unit price cannot be negative")
    return round_amount(qty * price)

def calculate_invoice_totals(
    items: List[Dict[str, Any]],
    tax_rate: Union[float, int, str, Decimal] = Decimal("18.0")
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate subtotal, tax amount, and total amount using Decimal arithmetic.
    
    Args:
        items: List of dicts or items with quantity and unit_price
        tax_rate: Tax rate as a percentage (e.g. 18.0 for 18%)
    
    Returns:
        Tuple of (subtotal, tax_amount, total_amount) as Decimals
    """
    tax_pct = to_decimal(tax_rate, default="0.00")
    if tax_pct < Decimal("0"):
        raise ValueError("Tax rate cannot be negative")

    subtotal = Decimal("0.00")
    for item in items:
        # Handle dict or object
        qty = item.get("quantity", 1) if isinstance(item, dict) else getattr(item, "quantity", 1)
        price = item.get("unit_price", 0) if isinstance(item, dict) else getattr(item, "unit_price", 0)
        item_total = calculate_item_total(qty, price)
        subtotal += item_total

    subtotal = round_amount(subtotal)
    tax_amount = round_amount((subtotal * tax_pct) / Decimal("100.00"))
    total_amount = round_amount(subtotal + tax_amount)

    return subtotal, tax_amount, total_amount

