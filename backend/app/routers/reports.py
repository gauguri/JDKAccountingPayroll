"""Financial reports with JSON / CSV / PDF export."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.services import reports, exporters

router = APIRouter(prefix="/companies/{company_id}/reports", tags=["reports"])


def _build(db, company_id, rtype, start, end):
    today = date.today()
    start = start or date(today.year, 1, 1)
    end = end or today
    if rtype == "pnl":
        return reports.profit_and_loss(db, company_id, start, end)
    if rtype == "balance_sheet":
        return reports.balance_sheet(db, company_id, end)
    if rtype == "trial_balance":
        return reports.trial_balance(db, company_id, end)
    if rtype == "general_ledger":
        return reports.general_ledger(db, company_id, start, end)
    raise HTTPException(400, "Unknown report type")


def _jsonable(obj):
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    return obj


@router.get("/{rtype}")
def get_report(company_id: str, rtype: str,
               from_: date | None = Query(None, alias="from"),
               to: date | None = Query(None),
               format: str = "json",
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    report = _build(db, company_id, rtype, from_, to)
    if format == "json":
        return JSONResponse(_jsonable(report))
    if format == "csv":
        return Response(exporters.to_csv(report), media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={rtype}.csv"})
    if format == "pdf":
        return Response(exporters.to_pdf(report), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={rtype}.pdf"})
    raise HTTPException(400, "format must be json, csv, or pdf")
