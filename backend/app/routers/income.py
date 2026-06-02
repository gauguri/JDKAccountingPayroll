"""Income entry with plain-English preview before posting."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.transactions import Income, Customer, PAYMENT_METHODS
from app.models.ledger import JournalEntry, JournalLine
from app.services.ledger import post_entry, reverse_entry
from app.services.entries import build_income
from app.services import audit
from app.schemas import IncomeIn, PreviewOut

router = APIRouter(prefix="/companies/{company_id}/income", tags=["income"])


def _customer(db, company_id, name):
    if not name:
        return None
    c = db.query(Customer).filter(Customer.company_id == company_id,
                                  Customer.name == name).first()
    if not c:
        c = Customer(company_id=company_id, name=name)
        db.add(c)
        db.flush()
    return c


@router.post("/preview", response_model=PreviewOut)
def preview(company_id: str, body: IncomeIn,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.payment_method not in PAYMENT_METHODS:
        raise HTTPException(400, f"Payment method must be one of {sorted(PAYMENT_METHODS)}")
    lines, explanation, _ = build_income(
        db, company_id, amount=body.amount, sales_tax_collected=body.sales_tax_collected,
        income_account_id=body.income_account_id, deposit_account_id=body.deposit_account_id,
        payment_method=body.payment_method,
    )
    return PreviewOut(
        explanation=explanation,
        lines=[{"account_name": l["account_name"], "debit": l["debit"], "credit": l["credit"]}
               for l in lines],
    )


@router.post("", status_code=201)
def create_income(company_id: str, body: IncomeIn,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.payment_method not in PAYMENT_METHODS:
        raise HTTPException(400, f"Payment method must be one of {sorted(PAYMENT_METHODS)}")
    lines, explanation, deposit_account_id = build_income(
        db, company_id, amount=body.amount, sales_tax_collected=body.sales_tax_collected,
        income_account_id=body.income_account_id, deposit_account_id=body.deposit_account_id,
        payment_method=body.payment_method,
    )
    customer = _customer(db, company_id, body.customer_name)
    income = Income(
        company_id=company_id, date=body.date, customer_id=customer.id if customer else None,
        amount=body.amount, payment_method=body.payment_method,
        account_id=body.income_account_id, deposit_account_id=deposit_account_id,
        sales_tax_collected=body.sales_tax_collected, taxable=body.taxable, notes=body.notes,
    )
    db.add(income)
    db.flush()
    entry = post_entry(
        db, company_id=company_id, entry_date=body.date,
        memo=f"Income: {body.notes or ''}".strip(), source_type="income",
        source_id=income.id, lines=lines, created_by=user.id,
    )
    income.journal_entry_id = entry.id
    audit.record(db, company_id=company_id, user_id=user.id, action="create",
                 entity_type="income", entity_id=income.id,
                 after={"amount": str(body.amount)})
    db.commit()
    return {"id": income.id, "journal_entry_id": entry.id, "explanation": explanation}


@router.get("")
def list_income(company_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = db.query(Income).filter(Income.company_id == company_id).order_by(
        Income.date.desc()).all()
    return [{"id": r.id, "date": str(r.date), "amount": str(r.amount),
             "payment_method": r.payment_method, "sales_tax_collected": str(r.sales_tax_collected),
             "taxable": r.taxable, "notes": r.notes} for r in rows]


@router.delete("/{income_id}")
def delete_income(company_id: str, income_id: str,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    income = db.get(Income, income_id)
    if not income or income.company_id != company_id:
        raise HTTPException(404, "Income not found")
    if income.journal_entry_id:
        entry = db.get(JournalEntry, income.journal_entry_id)
        if entry:
            reverse_entry(db, entry=entry, created_by=user.id)  # books stay intact
    db.delete(income)
    audit.record(db, company_id=company_id, user_id=user.id, action="delete",
                 entity_type="income", entity_id=income_id)
    db.commit()
    return {"ok": True}
