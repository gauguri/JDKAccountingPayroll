"""Double-entry posting and balance computation. The accounting core."""
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.money import money  # re-exported for existing callers
from app.models.ledger import JournalEntry, JournalLine
from app.models.account import Account


def post_entry(
    db: Session,
    *,
    company_id: str,
    entry_date: date,
    memo: str,
    source_type: str,
    lines: list[dict],
    source_id: str | None = None,
    created_by: str | None = None,
    flush: bool = True,
) -> JournalEntry:
    """Create a balanced journal entry. `lines`: [{account_id, debit, credit, memo}].

    Raises if debits != credits or fewer than two lines.
    """
    if len(lines) < 2:
        raise HTTPException(400, "A journal entry needs at least two lines")
    total_debit = sum((money(l.get("debit", 0)) for l in lines), Decimal("0"))
    total_credit = sum((money(l.get("credit", 0)) for l in lines), Decimal("0"))
    if total_debit != total_credit:
        raise HTTPException(
            400,
            f"Entry does not balance: debits {total_debit} != credits {total_credit}",
        )
    if total_debit == 0:
        raise HTTPException(400, "Entry total cannot be zero")

    entry = JournalEntry(
        company_id=company_id,
        entry_date=entry_date,
        memo=memo,
        source_type=source_type,
        source_id=source_id,
        posted=True,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()  # assign entry.id
    for l in lines:
        db.add(
            JournalLine(
                journal_entry_id=entry.id,
                account_id=l["account_id"],
                debit=money(l.get("debit", 0)),
                credit=money(l.get("credit", 0)),
                memo=l.get("memo"),
            )
        )
    if flush:
        db.flush()
    return entry


def reverse_entry(
    db: Session, *, entry: JournalEntry, created_by: str | None = None
) -> JournalEntry:
    """Post a mirror-image entry and link the two (books are never edited in place)."""
    rev_lines = [
        {
            "account_id": l.account_id,
            "debit": l.credit,
            "credit": l.debit,
            "memo": f"Reversal of {entry.id}",
        }
        for l in entry.lines
    ]
    rev = post_entry(
        db,
        company_id=entry.company_id,
        entry_date=entry.entry_date,
        memo=f"Reversal: {entry.memo or ''}",
        source_type=entry.source_type,
        source_id=entry.source_id,
        lines=rev_lines,
        created_by=created_by,
    )
    entry.reversed_by = rev.id
    db.flush()
    return rev


def account_balances(
    db: Session, company_id: str, start: date | None = None, end: date | None = None
) -> dict[str, Decimal]:
    """Net balance per account as a signed Decimal in the account's normal direction.

    Debit-normal accounts (asset/expense): debit - credit.
    Credit-normal accounts (liability/equity/income): credit - debit.
    """
    q = (
        db.query(
            JournalLine.account_id,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .filter(JournalEntry.company_id == company_id, JournalEntry.posted == True)  # noqa: E712
    )
    if start:
        q = q.filter(JournalEntry.entry_date >= start)
    if end:
        q = q.filter(JournalEntry.entry_date <= end)
    q = q.group_by(JournalLine.account_id)

    normals = {a.id: a.normal_balance for a in
               db.query(Account).filter(Account.company_id == company_id).all()}
    out: dict[str, Decimal] = {}
    for account_id, deb, cred in q.all():
        deb, cred = money(deb), money(cred)
        if normals.get(account_id) == "credit":
            out[account_id] = cred - deb
        else:
            out[account_id] = deb - cred
    return out
