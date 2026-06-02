"""Builds the journal lines + plain-English explanation for income and expenses.

Used by both the /preview endpoints (show, don't save) and the create endpoints
(save after the user confirms), so the preview always matches what gets posted.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.account import Account
from app.services.ledger import money
from app.services.coa import find_account


def _acct(db: Session, company_id: str, account_id: str) -> Account:
    a = db.get(Account, account_id)
    if not a or a.company_id != company_id:
        raise HTTPException(404, f"Account {account_id} not found")
    return a


def default_deposit_account(db: Session, company_id: str, payment_method: str) -> Account:
    name = "Cash" if payment_method == "cash" else "Checking Account"
    a = find_account(db, company_id, name) or find_account(db, company_id, "Checking Account")
    if not a:
        raise HTTPException(400, "No bank/cash account found to deposit into")
    return a


def default_paid_from_account(db: Session, company_id: str, payment_method: str) -> Account:
    name = "Credit Card" if payment_method == "credit_card" else (
        "Cash" if payment_method == "cash" else "Checking Account"
    )
    a = find_account(db, company_id, name) or find_account(db, company_id, "Checking Account")
    if not a:
        raise HTTPException(400, "No account found to pay from")
    return a


def build_income(db: Session, company_id: str, *, amount, sales_tax_collected,
                 income_account_id: str, deposit_account_id: str | None,
                 payment_method: str):
    amount = money(amount)
    tax = money(sales_tax_collected or 0)
    income_acct = _acct(db, company_id, income_account_id)
    deposit_acct = (
        _acct(db, company_id, deposit_account_id) if deposit_account_id
        else default_deposit_account(db, company_id, payment_method)
    )
    total = amount + tax
    lines = [
        {"account_id": deposit_acct.id, "debit": total, "credit": Decimal("0"),
         "account_name": deposit_acct.name},
        {"account_id": income_acct.id, "debit": Decimal("0"), "credit": amount,
         "account_name": income_acct.name},
    ]
    explanation = (
        f"This records ${amount} of income into '{income_acct.name}' and "
        f"increases '{deposit_acct.name}' by ${total}."
    )
    if tax > 0:
        tax_acct = find_account(db, company_id, "Sales Tax Payable")
        if not tax_acct:
            raise HTTPException(400, "Sales Tax Payable account is missing")
        lines.append({"account_id": tax_acct.id, "debit": Decimal("0"), "credit": tax,
                      "account_name": tax_acct.name})
        explanation += (
            f" ${tax} of that is sales tax you collected and now owe New Jersey "
            f"(tracked in '{tax_acct.name}')."
        )
    return lines, explanation, deposit_acct.id


def build_expense(db: Session, company_id: str, *, amount, expense_account_id: str,
                  paid_from_account_id: str | None, payment_method: str):
    amount = money(amount)
    expense_acct = _acct(db, company_id, expense_account_id)
    paid_acct = (
        _acct(db, company_id, paid_from_account_id) if paid_from_account_id
        else default_paid_from_account(db, company_id, payment_method)
    )
    lines = [
        {"account_id": expense_acct.id, "debit": amount, "credit": Decimal("0"),
         "account_name": expense_acct.name},
        {"account_id": paid_acct.id, "debit": Decimal("0"), "credit": amount,
         "account_name": paid_acct.name},
    ]
    verb = "increases what you owe on" if paid_acct.type == "liability" else "reduces"
    explanation = (
        f"This records ${amount} of '{expense_acct.name}' expense and {verb} "
        f"'{paid_acct.name}' by ${amount}."
    )
    return lines, explanation, paid_acct.id
