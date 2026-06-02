"""QuickBooks / data migration (Phase 1.5).

Live QuickBooks Online import uses Intuit's OAuth API, which needs a registered
Intuit developer app and outbound internet. That wiring is finished with the
owner's Intuit credentials. This module provides the migration endpoints and an
offline path: import from a QuickBooks CSV/Excel export, which works today.
"""
import csv
import io

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.transactions import Customer, Vendor

router = APIRouter(prefix="/companies/{company_id}/import", tags=["import"])


@router.get("/qbo/status")
def qbo_status(company_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    return {
        "connected": False,
        "message": ("Live QuickBooks Online connection requires Intuit app "
                    "credentials and is set up during deployment. You can import a "
                    "QuickBooks CSV/Excel export now via /import/list."),
    }


@router.post("/list/{kind}")
async def import_list(company_id: str, kind: str, file: UploadFile = File(...),
                      name_column: str = Form("Name"),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Import a simple list export (customers or vendors) from a QuickBooks CSV."""
    require_company(company_id, user, db)
    if kind not in {"customers", "vendors"}:
        raise HTTPException(400, "kind must be 'customers' or 'vendors'")
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if name_column not in (reader.fieldnames or []):
        raise HTTPException(400, f"Column '{name_column}' not found in file")

    created = skipped = 0
    Model = Customer if kind == "customers" else Vendor
    existing = {r.name for r in db.query(Model).filter(Model.company_id == company_id).all()}
    for row in reader:
        name = (row.get(name_column) or "").strip()
        if not name:
            continue
        if name in existing:
            skipped += 1
            continue
        db.add(Model(company_id=company_id, name=name))
        existing.add(name)
        created += 1
    db.commit()
    return {"kind": kind, "created": created, "skipped_duplicates": skipped}
