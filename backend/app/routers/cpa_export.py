"""One-click CPA export package: a ZIP of reports (CSV + PDF) and notes."""
import io
import zipfile
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.company import Company
from app.models.transactions import Expense
from app.services import reports, exporters, audit

router = APIRouter(prefix="/companies/{company_id}/cpa-export", tags=["cpa-export"])


@router.post("")
def build_package(company_id: str,
                  from_: date | None = Query(None, alias="from"),
                  to: date | None = Query(None),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    company = db.get(Company, company_id)
    today = date.today()
    start = from_ or date(today.year, 1, 1)
    end = to or today

    pnl = reports.profit_and_loss(db, company_id, start, end)
    bs = reports.balance_sheet(db, company_id, end)
    tb = reports.trial_balance(db, company_id, end)
    gl = reports.general_ledger(db, company_id, start, end)

    # Items the CPA should look at: expenses flagged for review.
    cpa_items = db.query(Expense).filter(
        Expense.company_id == company_id, Expense.cpa_review == True  # noqa: E712
    ).all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rpt, base in ((pnl, "profit_and_loss"), (bs, "balance_sheet"),
                          (tb, "trial_balance"), (gl, "general_ledger")):
            zf.writestr(f"reports/{base}.csv", exporters.to_csv(rpt))
            zf.writestr(f"reports/{base}.pdf", exporters.to_pdf(rpt))

        notes = [
            f"CPA Export Package for {company.name}",
            f"Entity type: {company.business_type}   State: {company.state}",
            f"Period: {start} to {end}",
            "",
            f"Net income for the period: {pnl['net_income']}",
            f"Balance sheet balances: {bs['balances']}",
            f"Trial balance balances: {tb['balances']}",
            "",
            "Items flagged for CPA review:",
        ]
        if cpa_items:
            for e in cpa_items:
                notes.append(f"  - {e.date}  ${e.amount}  {e.business_purpose or e.notes or ''}")
        else:
            notes.append("  (none)")
        notes += [
            "",
            "NOTE: This package was prepared by JDK Books for the owners' bookkeeping.",
            "It is for CPA review and tax preparation. It is not a filed tax return,",
            "and figures should be reviewed by the CPA.",
        ]
        zf.writestr("READ_ME_FIRST.txt", "\n".join(notes))
        zf.writestr("receipts/.keep", "Attached receipts would be placed here.")

    audit.record(db, company_id=company_id, user_id=user.id, action="export",
                 entity_type="cpa_package", after={"period": f"{start}..{end}"})
    db.commit()
    fname = f"cpa_package_{company.name.replace(' ', '_')}_{end}.zip"
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})
