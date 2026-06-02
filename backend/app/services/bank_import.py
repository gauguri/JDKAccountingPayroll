"""Parse a bank CSV using a column mapping, with duplicate detection."""
import csv
import hashlib
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from app.core.money import money


def _parse_date(raw: str) -> date:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not read date '{raw}'")


def _parse_amount(raw: str) -> Decimal:
    raw = (raw or "").strip().replace("$", "").replace(",", "")
    if raw in ("", "-"):
        return Decimal("0")
    neg = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    try:
        val = money(raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Could not read amount '{raw}'")
    return -val if neg else val


def dedupe_hash(company_id: str, d: date, desc: str, amount: Decimal) -> str:
    key = f"{company_id}|{d.isoformat()}|{(desc or '').strip().lower()}|{amount}"
    return hashlib.sha256(key.encode()).hexdigest()


def parse_csv(content: str, column_map: dict, company_id: str) -> list[dict]:
    """Return parsed rows: [{date, description, amount, direction, dedupe_hash}].

    column_map maps logical fields to CSV header names:
      {"date": "Date", "description": "Description",
       "amount": "Amount"}  OR  {"debit": "Withdrawal", "credit": "Deposit"}
    """
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for raw in reader:
        d = _parse_date(raw.get(column_map["date"], ""))
        desc = raw.get(column_map.get("description", ""), "") if column_map.get("description") else ""
        if "amount" in column_map:
            amt = _parse_amount(raw.get(column_map["amount"], "0"))
        else:  # separate debit/credit columns — each is a positive magnitude
            debit = abs(_parse_amount(raw.get(column_map.get("debit", ""), "0")))
            credit = abs(_parse_amount(raw.get(column_map.get("credit", ""), "0")))
            amt = credit - debit
        direction = "credit" if amt >= 0 else "debit"
        rows.append({
            "date": d, "description": desc.strip(), "amount": abs(amt),
            "direction": direction,
            "dedupe_hash": dedupe_hash(company_id, d, desc, abs(amt)),
        })
    return rows
