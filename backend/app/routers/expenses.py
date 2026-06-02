"""Expense entry with plain-English preview before posting."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.transactions import Expense, Vendor, PAYMENT_METHODS
from app.models.ledger import JournalEntry
from app.services.ledger import post_entry, reverse_entry
from app.services.entries import build_expense
from app.services import audit
from app.schemas import ExpenseIn, PreviewOut

router = APIRouter(prefix="/companies/{company_id}/expenses", tags=["expenses"])


def _vendor(db, company_id, name):
    if not name:
        return None
    v = db.query(Vendor).filter(Vendor.company_id == company_id,
                                Vendor.name == name).first()
    if not v:
        v = Vendor(company_id=company_id, name=name)
        db.add(v)
        db.flush()
    return v


@router.post("/preview", response_model=PreviewOut)
def preview(company_id: str, body: ExpenseIn,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.payment_method not in PAYMENT_METHODS:
        raise HTTPException(400, f"Payment method must be one of {sorted(PAYMENT_METHODS)}")
    lines, explanation, _ = build_expense(
        db, company_id, amount=body.amount, expense_account_id=body.expense_account_id,
        paid_from_account_id=body.paid_from_account_id, payment_method=body.payment_method,
    )
    return PreviewOut(
        explanation=explanation,
        lines=[{"account_name": l["account_name"], "debit": l["debit"], "credit": l["credit"]}
               for l in lines],
    )


@router.post("", status_code=201)
def create_expense(company_id: str, body: ExpenseIn,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.payment_method not in PAYMENT_METHODS:
        raise HTTPException(400, f"Payment method must be one of {sorted(PAYMENT_METHODS)}")
    lines, explanation, paid_from_account_id = build_expense(
        db, company_id, amount=body.amount, expense_account_id=body.expense_account_id,
        paid_from_account_id=body.paid_from_account_id, payment_method=body.payment_method,
    )
    vendor = _vendor(db, company_id, body.vendor_name)
    expense = Expense(
        company_id=company_id, date=body.date, vendor_id=vendor.id if vendor else None,
        amount=body.amount, payment_method=body.payment_method,
        account_id=body.expense_account_id, paid_from_account_id=paid_from_account_id,
        business_purpose=body.business_purpose, reimbursable=body.reimbursable,
        tax_deductible=body.tax_deductible, cpa_review=body.cpa_review, notes=body.notes,
    )
    db.add(expense)
    db.flush()
    entry = post_entry(
        db, company_id=company_id, entry_date=body.date,
        memo=f"Expense: {body.business_purpose or body.notes or ''}".strip(),
        source_type="expense", source_id=expense.id, lines=lines, created_by=user.id,
    )
    expense.journal_entry_id = entry.id
    audit.record(db, company_id=company_id, user_id=user.id, action="create",
                 entity_type="expense", entity_id=expense.id,
                 after={"amount": str(body.amount), "cpa_review": body.cpa_review})
    db.commit()
    return {"id": expense.id, "journal_entry_id": entry.id, "explanation": explanation}


@router.get("")
def list_expenses(company_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = db.query(Expense).filter(Expense.company_id == company_id).order_by(
        Expense.date.desc()).all()
    return [{"id": r.id, "date": str(r.date), "amount": str(r.amount),
             "payment_method": r.payment_method, "tax_deductible": r.tax_deductible,
             "cpa_review": r.cpa_review, "notes": r.notes} for r in rows]


@router.delete("/{expense_id}")
def delete_expense(company_id: str, expense_id: str,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    expense = db.get(Expense, expense_id)
    if not expense or expense.company_id != company_id:
        raise HTTPException(404, "Expense not found")
    if expense.journal_entry_id:
        entry = db.get(JournalEntry, expense.journal_entry_id)
        if entry:
            reverse_entry(db, entry=entry, created_by=user.id)
    db.delete(expense)
    audit.record(db, company_id=company_id, user_id=user.id, action="delete",
                 entity_type="expense", entity_id=expense_id)
    db.commit()
    return {"ok": True}
