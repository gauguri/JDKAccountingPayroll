"""Chart of accounts: list, add, edit, hide, suggest. Deletion guarded."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.account import Account, ACCOUNT_TYPES, NORMAL_BALANCE
from app.models.ledger import JournalLine
from app.services.coa import suggest_account_name, find_account
from app.services import audit
from app.schemas import AccountIn, AccountOut

router = APIRouter(prefix="/companies/{company_id}/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(company_id: str, include_hidden: bool = False,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    q = db.query(Account).filter(Account.company_id == company_id)
    if not include_hidden:
        q = q.filter(Account.hidden == False)  # noqa: E712
    return q.order_by(Account.code).all()


@router.post("", response_model=AccountOut, status_code=201)
def add_account(company_id: str, body: AccountIn,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.type not in ACCOUNT_TYPES:
        raise HTTPException(400, f"Type must be one of {sorted(ACCOUNT_TYPES)}")
    acct = Account(
        company_id=company_id, name=body.name, type=body.type, subtype=body.subtype,
        code=body.code, description_plain=body.description_plain,
        normal_balance=NORMAL_BALANCE[body.type], system_locked=False,
    )
    db.add(acct)
    audit.record(db, company_id=company_id, user_id=user.id, action="create",
                 entity_type="account", entity_id=acct.id, after={"name": acct.name})
    db.commit()
    db.refresh(acct)
    return acct


@router.put("/{account_id}", response_model=AccountOut)
def edit_account(company_id: str, account_id: str, body: AccountIn,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    acct = db.get(Account, account_id)
    if not acct or acct.company_id != company_id:
        raise HTTPException(404, "Account not found")
    acct.name = body.name
    acct.description_plain = body.description_plain
    if not acct.system_locked:
        acct.subtype = body.subtype
        acct.code = body.code
    db.commit()
    db.refresh(acct)
    return acct


@router.post("/{account_id}/hide", response_model=AccountOut)
def hide_account(company_id: str, account_id: str, hidden: bool = True,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    acct = db.get(Account, account_id)
    if not acct or acct.company_id != company_id:
        raise HTTPException(404, "Account not found")
    acct.hidden = hidden
    db.commit()
    db.refresh(acct)
    return acct


@router.delete("/{account_id}")
def delete_account(company_id: str, account_id: str,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    acct = db.get(Account, account_id)
    if not acct or acct.company_id != company_id:
        raise HTTPException(404, "Account not found")
    if acct.system_locked:
        raise HTTPException(400, "This is a built-in account. You can hide it instead of deleting.")
    has_tx = db.query(JournalLine).filter(JournalLine.account_id == account_id).first()
    if has_tx:
        raise HTTPException(
            400, "This account has transactions and can't be deleted. Hide it instead."
        )
    db.delete(acct)
    audit.record(db, company_id=company_id, user_id=user.id, action="delete",
                 entity_type="account", entity_id=account_id)
    db.commit()
    return {"ok": True}


@router.get("/suggest")
def suggest(company_id: str, desc: str = Query(""),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    name = suggest_account_name(desc)
    if not name:
        return {"account_id": None, "account_name": None}
    acct = find_account(db, company_id, name)
    return {"account_id": acct.id if acct else None, "account_name": name}
