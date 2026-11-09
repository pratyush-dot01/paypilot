import uuid
from datetime import datetime

def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier with an optional prefix."""
    unique_part = uuid.uuid4().hex[:12]
    return f"{prefix}{unique_part}" if prefix else unique_part

def generate_invoice_number(sequence: int = 1, year: int = None, prefix: str = "INV") -> str:
    """
    Generate a formatted invoice number like INV-2026-0001.
    """
    if year is None:
        year = datetime.now().year
    return f"{prefix}-{year}-{sequence:04d}"

