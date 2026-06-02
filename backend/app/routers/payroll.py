"""Payroll: employees, employer setup, and the run wizard (calculate -> approve -> post)."""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.core.security import encrypt_field, decrypt_field, mask_tail
from app.models.user import User
from app.models.company import Company
from app.models.payroll import (
    Employee, EmployerPayrollSetup, PayrollRun, PayrollItem, PAY_TYPES, FILING_STATUSES,
)
from app.services import payroll as payroll_svc, audit
from app.services.ledger import post_entry, money
from app.services.coa import find_account
from app.schemas import EmployeeIn, EmployeeOut, EmployerSetupIn, PayrollRunIn

router = APIRouter(prefix="/companies/{company_id}/payroll", tags=["payroll"])


def _emp_out(e: Employee) -> EmployeeOut:
    ssn = decrypt_field(e.ssn_encrypted) if e.ssn_encrypted else None
    return EmployeeOut(
        id=e.id, first_name=e.first_name, last_name=e.last_name, pay_type=e.pay_type,
        pay_rate=e.pay_rate, filing_status=e.filing_status,
        ssn_masked=mask_tail(ssn) if ssn else None, is_active=e.is_active,
    )


# ---- employees ----
@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(company_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    return [_emp_out(e) for e in
            db.query(Employee).filter(Employee.company_id == company_id).all()]


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def add_employee(company_id: str, body: EmployeeIn,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    if body.pay_type not in PAY_TYPES:
        raise HTTPException(400, "pay_type must be 'hourly' or 'salary'")
    if body.filing_status not in FILING_STATUSES:
        raise HTTPException(400, f"filing_status must be one of {sorted(FILING_STATUSES)}")
    e = Employee(
        company_id=company_id, first_name=body.first_name, last_name=body.last_name,
        address=body.address, email=body.email, pay_type=body.pay_type,
        pay_rate=body.pay_rate, filing_status=body.filing_status,
        fed_extra_withholding=body.fed_extra_withholding,
        state_extra_withholding=body.state_extra_withholding,
        start_date=body.start_date, is_active=body.is_active,
        ssn_encrypted=encrypt_field(body.ssn),
        dd_info_encrypted=encrypt_field(body.direct_deposit),
    )
    db.add(e)
    audit.record(db, company_id=company_id, user_id=user.id, action="create",
                 entity_type="employee", entity_id=e.id,
                 after={"name": f"{e.first_name} {e.last_name}"})  # no SSN in audit
    db.commit()
    db.refresh(e)
    return _emp_out(e)


# ---- employer setup ----
@router.get("/setup")
def get_setup(company_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    s = db.query(EmployerPayrollSetup).filter(
        EmployerPayrollSetup.company_id == company_id).first()
    if not s:
        return {"payroll_schedule": "biweekly", "suta_rate": "0",
                "state_employer_id_masked": None}
    sid = decrypt_field(s.state_employer_id_encrypted) if s.state_employer_id_encrypted else None
    return {"payroll_schedule": s.payroll_schedule, "suta_rate": str(s.suta_rate),
            "state_employer_id_masked": mask_tail(sid) if sid else None}


@router.put("/setup")
def put_setup(company_id: str, body: EmployerSetupIn,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    s = db.query(EmployerPayrollSetup).filter(
        EmployerPayrollSetup.company_id == company_id).first()
    if not s:
        s = EmployerPayrollSetup(company_id=company_id)
        db.add(s)
    s.payroll_schedule = body.payroll_schedule
    s.suta_rate = body.suta_rate
    if body.state_employer_id is not None:
        s.state_employer_id_encrypted = encrypt_field(body.state_employer_id)
    audit.record(db, company_id=company_id, user_id=user.id, action="update",
                 entity_type="employer_payroll_setup", entity_id=s.id)
    db.commit()
    return {"ok": True}


# ---- payroll run ----
def _setup(db, company_id):
    s = db.query(EmployerPayrollSetup).filter(
        EmployerPayrollSetup.company_id == company_id).first()
    schedule = s.payroll_schedule if s else "biweekly"
    suta_rate = s.suta_rate if s else money(0)
    return schedule, suta_rate


@router.post("/runs", status_code=201)
def create_and_calculate(company_id: str, body: PayrollRunIn,
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a run and calculate every employee's pay (status -> 'calculated').

    Nothing is posted to the books yet — the user reviews, then approves+posts.
    """
    require_company(company_id, user, db)
    company = db.get(Company, company_id)
    schedule, suta_rate = _setup(db, company_id)
    year = body.pay_date.year
    rs = payroll_svc.load_rulesets(db, company.state, year)

    run = PayrollRun(company_id=company_id, pay_period_start=body.pay_period_start,
                     pay_period_end=body.pay_period_end, pay_date=body.pay_date,
                     status="calculated", created_by=user.id)
    db.add(run)
    db.flush()

    hours_map = {h.employee_id: h.hours for h in body.hours}
    versions_all = {}
    for emp in db.query(Employee).filter(Employee.company_id == company_id,
                                         Employee.is_active == True).all():  # noqa: E712
        hrs = hours_map.get(emp.id, 0)
        ytd = payroll_svc.ytd_gross(db, emp.id, year, body.pay_date)
        calc = payroll_svc.calculate(emp, money(hrs), schedule, ytd, suta_rate, rs)
        versions_all.update(calc["versions"])
        db.add(PayrollItem(
            payroll_run_id=run.id, employee_id=emp.id, hours=money(hrs),
            gross_pay=calc["gross_pay"], fed_wh=calc["fed_wh"], state_wh=calc["state_wh"],
            ss_employee=calc["ss_employee"], medicare_employee=calc["medicare_employee"],
            ss_employer=calc["ss_employer"], medicare_employer=calc["medicare_employer"],
            futa=calc["futa"], suta=calc["suta"], net_pay=calc["net_pay"],
            calc_explanation_json=json.dumps(calc["explanation"]),
        ))
    run.tax_versions_json = json.dumps(versions_all)
    db.commit()
    return get_run(company_id, run.id, user, db)


@router.get("/runs")
def list_runs(company_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    runs = db.query(PayrollRun).filter(PayrollRun.company_id == company_id).order_by(
        PayrollRun.pay_date.desc()).all()
    return [{"id": r.id, "pay_date": str(r.pay_date), "status": r.status,
             "period": f"{r.pay_period_start} to {r.pay_period_end}"} for r in runs]


@router.get("/runs/{run_id}")
def get_run(company_id: str, run_id: str, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    run = db.get(PayrollRun, run_id)
    if not run or run.company_id != company_id:
        raise HTTPException(404, "Payroll run not found")
    emps = {e.id: e for e in db.query(Employee).filter(Employee.company_id == company_id).all()}
    items = []
    totals = {k: money(0) for k in ("gross_pay", "fed_wh", "state_wh", "ss_employee",
              "medicare_employee", "ss_employer", "medicare_employer", "futa", "suta", "net_pay")}
    for it in run.items:
        e = emps.get(it.employee_id)
        items.append({
            "id": it.id,
            "employee": f"{e.first_name} {e.last_name}" if e else "?",
            "hours": str(it.hours), "gross_pay": str(it.gross_pay),
            "fed_wh": str(it.fed_wh), "state_wh": str(it.state_wh),
            "ss_employee": str(it.ss_employee), "medicare_employee": str(it.medicare_employee),
            "ss_employer": str(it.ss_employer), "medicare_employer": str(it.medicare_employer),
            "futa": str(it.futa), "suta": str(it.suta), "net_pay": str(it.net_pay),
        })
        for k in totals:
            totals[k] += money(getattr(it, k))
    return {
        "id": run.id, "status": run.status, "pay_date": str(run.pay_date),
        "period": f"{run.pay_period_start} to {run.pay_period_end}",
        "items": items, "totals": {k: str(v) for k, v in totals.items()},
        "disclaimer": "Estimated from SAMPLE tax tables in DRAFT status. Review with your CPA before paying.",
    }


@router.post("/runs/{run_id}/post")
def approve_and_post(company_id: str, run_id: str,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Approve the run and post the payroll journal entry to the books."""
    require_company(company_id, user, db)
    run = db.get(PayrollRun, run_id)
    if not run or run.company_id != company_id:
        raise HTTPException(404, "Payroll run not found")
    if run.status == "posted":
        raise HTTPException(400, "This payroll was already posted")

    gross = sum((money(i.gross_pay) for i in run.items), money(0))
    employee_wh = sum((money(i.fed_wh) + money(i.state_wh) + money(i.ss_employee)
                       + money(i.medicare_employee) for i in run.items), money(0))
    employer_tax = sum((money(i.ss_employer) + money(i.medicare_employer)
                        + money(i.futa) + money(i.suta) for i in run.items), money(0))
    net = sum((money(i.net_pay) for i in run.items), money(0))
    if gross == 0:
        raise HTTPException(400, "Nothing to post — gross pay is zero")

    wages = find_account(db, company_id, "Payroll Wages")
    ptax_exp = find_account(db, company_id, "Payroll Taxes")
    checking = find_account(db, company_id, "Checking Account")
    ptax_pay = find_account(db, company_id, "Payroll Taxes Payable")

    lines = [
        {"account_id": wages.id, "debit": gross, "credit": 0},
        {"account_id": ptax_exp.id, "debit": employer_tax, "credit": 0},
        {"account_id": checking.id, "debit": 0, "credit": net},
        {"account_id": ptax_pay.id, "debit": 0, "credit": employee_wh + employer_tax},
    ]
    entry = post_entry(db, company_id=company_id, entry_date=run.pay_date,
                       memo=f"Payroll for {run.pay_period_start}–{run.pay_period_end}",
                       source_type="payroll", source_id=run.id, lines=lines,
                       created_by=user.id)
    run.journal_entry_id = entry.id
    run.status = "posted"
    audit.record(db, company_id=company_id, user_id=user.id, action="post",
                 entity_type="payroll_run", entity_id=run.id,
                 after={"gross": str(gross), "net": str(net)})
    db.commit()
    return {"ok": True, "journal_entry_id": entry.id,
            "gross": str(gross), "net": str(net), "employer_tax": str(employer_tax)}
