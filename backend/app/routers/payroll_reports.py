"""Payroll tax reports + pay-stub PDFs + 941/940 worksheets. CPA-ready, no filing."""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.models.user import User
from app.models.company import Company
from app.models.payroll import PayrollRun, PayrollItem, Employee
from app.services.ledger import money
from app.services.paystub import paystub_pdf

router = APIRouter(prefix="/companies/{company_id}/payroll", tags=["payroll-reports"])

_FIELDS = ("gross_pay", "fed_wh", "state_wh", "ss_employee", "medicare_employee",
           "ss_employer", "medicare_employer", "futa", "suta", "net_pay")


def _runs_in_period(db, company_id, start, end):
    return (db.query(PayrollRun)
            .filter(PayrollRun.company_id == company_id,
                    PayrollRun.pay_date >= start, PayrollRun.pay_date <= end,
                    PayrollRun.status.in_(("calculated", "approved", "posted")))
            .all())


@router.get("/runs/{run_id}/stubs/{item_id}")
def pay_stub(company_id: str, run_id: str, item_id: str,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    run = db.get(PayrollRun, run_id)
    item = db.get(PayrollItem, item_id)
    if not run or run.company_id != company_id or not item or item.payroll_run_id != run_id:
        raise HTTPException(404, "Pay stub not found")
    company = db.get(Company, company_id)
    emp = db.get(Employee, item.employee_id)
    pdf = paystub_pdf(
        company_name=company.name, employee_name=f"{emp.first_name} {emp.last_name}",
        pay_date=str(run.pay_date), period=f"{run.pay_period_start} to {run.pay_period_end}",
        item={f: str(getattr(item, f)) for f in _FIELDS} | {"hours": str(item.hours)},
    )
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=paystub_{item_id}.pdf"})


@router.get("/reports/{rtype}")
def payroll_report(company_id: str, rtype: str,
                   from_: date | None = Query(None, alias="from"),
                   to: date | None = Query(None),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    today = date.today()
    start = from_ or date(today.year, 1, 1)
    end = to or date(today.year, 12, 31)
    runs = _runs_in_period(db, company_id, start, end)
    emps = {e.id: e for e in db.query(Employee).filter(Employee.company_id == company_id).all()}

    if rtype == "employee_earnings":
        per_emp = {}
        for run in runs:
            for it in run.items:
                acc = per_emp.setdefault(it.employee_id, {f: money(0) for f in _FIELDS})
                for f in _FIELDS:
                    acc[f] += money(getattr(it, f))
        rows = [{"employee": f"{emps[eid].first_name} {emps[eid].last_name}"
                 if eid in emps else "?", **{f: str(v) for f, v in vals.items()}}
                for eid, vals in per_emp.items()]
        return JSONResponse({"report": "Employee Earnings",
                             "from": str(start), "to": str(end), "rows": rows})

    totals = {f: money(0) for f in _FIELDS}
    for run in runs:
        for it in run.items:
            for f in _FIELDS:
                totals[f] += money(getattr(it, f))

    if rtype == "payroll_summary":
        return JSONResponse({"report": "Payroll Summary", "from": str(start), "to": str(end),
                             "totals": {f: str(v) for f, v in totals.items()}})

    if rtype == "employer_taxes":
        et = {k: str(totals[k]) for k in ("ss_employer", "medicare_employer", "futa", "suta")}
        et["total"] = str(totals["ss_employer"] + totals["medicare_employer"]
                          + totals["futa"] + totals["suta"])
        return JSONResponse({"report": "Employer Taxes", "from": str(start),
                             "to": str(end), "employer_taxes": et})

    if rtype == "tax_liability":
        # What the employer must remit: employee withholdings + employer share.
        fed_liability = (totals["fed_wh"] + totals["ss_employee"] + totals["medicare_employee"]
                         + totals["ss_employer"] + totals["medicare_employer"])
        return JSONResponse({
            "report": "Payroll Tax Liability", "from": str(start), "to": str(end),
            "federal_941_liability": str(fed_liability),
            "federal_unemployment_940_futa": str(totals["futa"]),
            "state_withholding": str(totals["state_wh"]),
            "state_unemployment_suta": str(totals["suta"]),
            "disclaimer": "Estimated from sample DRAFT tax tables. For CPA review, not filing.",
        })

    if rtype == "form941_worksheet":
        return JSONResponse({
            "report": "Form 941 Worksheet (data only — not a filing)",
            "from": str(start), "to": str(end),
            "wages_tips_compensation": str(totals["gross_pay"]),
            "federal_income_tax_withheld": str(totals["fed_wh"]),
            "taxable_social_security_wages": str(totals["gross_pay"]),
            "social_security_tax": str(totals["ss_employee"] + totals["ss_employer"]),
            "medicare_tax": str(totals["medicare_employee"] + totals["medicare_employer"]),
            "note": "Worksheet data for your CPA. JDK Books does not file Form 941.",
        })

    if rtype == "form940_worksheet":
        return JSONResponse({
            "report": "Form 940 Worksheet (data only — not a filing)",
            "from": str(start), "to": str(end),
            "total_payments_to_employees": str(totals["gross_pay"]),
            "futa_tax": str(totals["futa"]),
            "note": "Worksheet data for your CPA. JDK Books does not file Form 940.",
        })

    raise HTTPException(400, "Unknown payroll report type")
