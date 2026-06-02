"""Financial reports computed from the ledger. P&L, Balance Sheet, Trial Balance, GL."""
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.ledger import JournalEntry, JournalLine
from app.services.ledger import money

Z = Decimal("0.00")


def _accounts(db: Session, company_id: str) -> list[Account]:
    return db.query(Account).filter(Account.company_id == company_id).order_by(
        Account.code).all()


def _raw_sums(db: Session, company_id: str, start, end) -> dict[str, tuple]:
    q = (
        db.query(JournalLine.account_id,
                 func.coalesce(func.sum(JournalLine.debit), 0),
                 func.coalesce(func.sum(JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .filter(JournalEntry.company_id == company_id, JournalEntry.posted == True)  # noqa: E712
    )
    if start:
        q = q.filter(JournalEntry.entry_date >= start)
    if end:
        q = q.filter(JournalEntry.entry_date <= end)
    q = q.group_by(JournalLine.account_id)
    return {aid: (money(d), money(c)) for aid, d, c in q.all()}


def _normal_balance(acct: Account, debit_sum: Decimal, credit_sum: Decimal) -> Decimal:
    if acct.normal_balance == "credit":
        return credit_sum - debit_sum
    return debit_sum - credit_sum


def profit_and_loss(db: Session, company_id: str, start: date, end: date) -> dict:
    sums = _raw_sums(db, company_id, start, end)
    income, expense = [], []
    total_income = total_expense = Z
    for a in _accounts(db, company_id):
        d, c = sums.get(a.id, (Z, Z))
        bal = _normal_balance(a, d, c)
        if a.type == "income" and bal != 0:
            income.append({"account": a.name, "amount": bal})
            total_income += bal
        elif a.type == "expense" and bal != 0:
            expense.append({"account": a.name, "amount": bal})
            total_expense += bal
    net = total_income - total_expense
    return {
        "report": "Profit & Loss", "start": str(start), "end": str(end),
        "income": income, "total_income": total_income,
        "expense": expense, "total_expense": total_expense,
        "net_income": net,
        "explanation": (
            f"You brought in ${total_income} and spent ${total_expense}, "
            f"for a {'profit' if net >= 0 else 'loss'} of ${abs(net)}."
        ),
    }


def balance_sheet(db: Session, company_id: str, as_of: date) -> dict:
    sums = _raw_sums(db, company_id, None, as_of)
    assets, liabilities, equity = [], [], []
    t_assets = t_liab = t_equity = Z
    income_total = expense_total = Z
    for a in _accounts(db, company_id):
        d, c = sums.get(a.id, (Z, Z))
        bal = _normal_balance(a, d, c)
        if a.type == "asset":
            if bal != 0:
                assets.append({"account": a.name, "amount": bal})
            t_assets += bal
        elif a.type == "liability":
            if bal != 0:
                liabilities.append({"account": a.name, "amount": bal})
            t_liab += bal
        elif a.type == "equity":
            if bal != 0:
                equity.append({"account": a.name, "amount": bal})
            t_equity += bal
        elif a.type == "income":
            income_total += bal
        elif a.type == "expense":
            expense_total += bal
    # Net income flows into equity so the sheet balances (not yet closed to retained earnings).
    net_income = income_total - expense_total
    equity.append({"account": "Net Income (this period, not yet closed)", "amount": net_income})
    t_equity += net_income
    return {
        "report": "Balance Sheet", "as_of": str(as_of),
        "assets": assets, "total_assets": t_assets,
        "liabilities": liabilities, "total_liabilities": t_liab,
        "equity": equity, "total_equity": t_equity,
        "balances": t_assets == (t_liab + t_equity),
        "explanation": (
            f"You own ${t_assets} in assets, owe ${t_liab}, leaving ${t_equity} "
            f"of value for the owners."
        ),
    }


def trial_balance(db: Session, company_id: str, as_of: date) -> dict:
    sums = _raw_sums(db, company_id, None, as_of)
    rows = []
    total_debit = total_credit = Z
    for a in _accounts(db, company_id):
        d, c = sums.get(a.id, (Z, Z))
        net = d - c  # raw: positive => net debit, negative => net credit
        if net == 0:
            continue
        debit_col = net if net > 0 else Z
        credit_col = -net if net < 0 else Z
        rows.append({"code": a.code, "account": a.name,
                     "debit": debit_col, "credit": credit_col})
        total_debit += debit_col
        total_credit += credit_col
    return {
        "report": "Trial Balance", "as_of": str(as_of), "rows": rows,
        "total_debit": total_debit, "total_credit": total_credit,
        "balances": total_debit == total_credit,
    }


def general_ledger(db: Session, company_id: str, start: date, end: date) -> dict:
    accts = {a.id: a for a in _accounts(db, company_id)}
    q = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .filter(JournalEntry.company_id == company_id)
    )
    if start:
        q = q.filter(JournalEntry.entry_date >= start)
    if end:
        q = q.filter(JournalEntry.entry_date <= end)
    q = q.order_by(JournalEntry.entry_date)
    lines = []
    for line, entry in q.all():
        a = accts.get(line.account_id)
        lines.append({
            "date": str(entry.entry_date), "account": a.name if a else "?",
            "memo": entry.memo, "debit": money(line.debit), "credit": money(line.credit),
        })
    return {"report": "General Ledger", "start": str(start), "end": str(end),
            "lines": lines}
