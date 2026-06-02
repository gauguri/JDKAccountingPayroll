"""Money helper. Kept dependency-free so the accounting math is unit-testable
without the web stack."""
from decimal import Decimal, ROUND_HALF_UP


def money(value) -> Decimal:
    """Quantize any numeric/string value to 2 decimal places (banker's-safe)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
