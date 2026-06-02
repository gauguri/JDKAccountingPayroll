"""Bank CSV import: upload, preview (with duplicate flags), commit, list."""
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.bank import BankImportBatch, BankTransaction, BankCsvMapping
from app.services import bank_import, audit
from app.services.coa import suggest_account_name, find_account

router = APIRouter(prefix="/companies/{company_id}/bank", tags=["bank"])


@router.get("/mappings")
def list_mappings(company_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = db.query(BankCsvMapping).filter(BankCsvMapping.company_id == company_id).all()
    return [{"id": r.id, "bank_label": r.bank_label, "column_map": json.loads(r.column_map)}
            for r in rows]


@router.post("/import")
async def import_csv(company_id: str, bank_label: str = Form(...),
                     column_map: str = Form(...), file: UploadFile = File(...),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload a CSV with a column mapping. Parses, flags duplicates, stores a batch."""
    require_company(company_id, user, db)
    try:
        cmap = json.loads(column_map)
    except json.JSONDecodeError:
        raise HTTPException(400, "column_map must be valid JSON")
    if "date" not in cmap:
        raise HTTPException(400, "column_map must include a 'date' field")

    content = (await file.read()).decode("utf-8-sig")
    try:
        parsed = bank_import.parse_csv(content, cmap, company_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Remember this bank's mapping for next time.
    existing = db.query(BankCsvMapping).filter(
        BankCsvMapping.company_id == company_id,
        BankCsvMapping.bank_label == bank_label).first()
    if existing:
        existing.column_map = json.dumps(cmap)
    else:
        db.add(BankCsvMapping(company_id=company_id, bank_label=bank_label,
                              column_map=json.dumps(cmap)))

    batch = BankImportBatch(company_id=company_id, bank_label=bank_label,
                            filename=file.filename, row_count=len(parsed), status="preview")
    db.add(batch)
    db.flush()

    seen_hashes = {
        h[0] for h in db.query(BankTransaction.dedupe_hash).filter(
            BankTransaction.company_id == company_id).all()
    }
    preview = []
    for row in parsed:
        is_dup = row["dedupe_hash"] in seen_hashes
        status = "needs_review" if is_dup else "unmatched"
        bt = BankTransaction(
            company_id=company_id, batch_id=batch.id, date=row["date"],
            description=row["description"], amount=row["amount"],
            direction=row["direction"], status=status, dedupe_hash=row["dedupe_hash"],
        )
        db.add(bt)
        db.flush()
        suggested = suggest_account_name(row["description"])
        sug_acct = find_account(db, company_id, suggested) if suggested else None
        preview.append({
            "id": bt.id, "date": str(row["date"]), "description": row["description"],
            "amount": str(row["amount"]), "direction": row["direction"],
            "duplicate": is_dup, "suggested_account": suggested,
            "suggested_account_id": sug_acct.id if sug_acct else None,
        })

    audit.record(db, company_id=company_id, user_id=user.id, action="import",
                 entity_type="bank_batch", entity_id=batch.id,
                 after={"rows": len(parsed), "bank": bank_label})
    db.commit()
    duplicates = sum(1 for p in preview if p["duplicate"])
    return {"batch_id": batch.id, "row_count": len(parsed),
            "duplicates": duplicates, "transactions": preview}


@router.get("/transactions")
def list_transactions(company_id: str, status: str | None = None,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    q = db.query(BankTransaction).filter(BankTransaction.company_id == company_id)
    if status:
        q = q.filter(BankTransaction.status == status)
    rows = q.order_by(BankTransaction.date.desc()).all()
    return [{"id": r.id, "date": str(r.date), "description": r.description,
             "amount": str(r.amount), "direction": r.direction, "status": r.status}
            for r in rows]


@router.post("/transactions/{tx_id}/status")
def set_status(company_id: str, tx_id: str, status: str,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    tx = db.get(BankTransaction, tx_id)
    if not tx or tx.company_id != company_id:
        raise HTTPException(404, "Transaction not found")
    if status not in {"unmatched", "matched", "needs_review", "added", "ignored"}:
        raise HTTPException(400, "Invalid status")
    tx.status = status
    db.commit()
    return {"ok": True, "status": status}
