"""Payroll calculation engine. Reads all rates from the tax-rule engine and
records which ruleset versions were used. No rate is hardcoded here."""
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.money import money
from app.models.payroll import Employee, PayrollItem, PayrollRun, EmployerPayrollSetup
from app.services import tax_rules as tr

PERIODS = {"weekly": 26 * 2, "biweekly": 26, "semimonthly": 24, "monthly": 12}
PERIODS["weekly"] = 52


def periods_per_year(schedule: str) -> int:
    return PERIODS.get(schedule, 26)


def ytd_gross(db: Session, employee_id: str, year: int, before: date) -> Decimal:
    """Sum of gross pay already paid to this employee earlier in the year."""
    total = (
        db.query(func.coalesce(func.sum(PayrollItem.gross_pay), 0))
        .join(PayrollRun, PayrollRun.id == PayrollItem.payroll_run_id)
        .filter(PayrollItem.employee_id == employee_id,
                func.extract("year", PayrollRun.pay_date) == year,
                PayrollRun.pay_date < before,
                PayrollRun.status.in_(("calculated", "approved", "posted")))
        .scalar()
    )
    return money(total or 0)


def load_rulesets(db: Session, state: str, year: int) -> dict:
    rs = {
        "ss": tr.get_ruleset(db, "US", "ss", year),
        "medicare": tr.get_ruleset(db, "US", "medicare", year),
        "addl_medicare": tr.get_ruleset(db, "US", "addl_medicare", year),
        "futa": tr.get_ruleset(db, "US", "futa", year),
        "suta": tr.get_ruleset(db, state, "suta", year),
        "fed_wh": tr.get_ruleset(db, "US", "fed_withholding", year),
        "state_wh": tr.get_ruleset(db, state, "state_withholding", year),
    }
    return rs


def _capped(base_wage: Decimal, ytd: Decimal, wage_base: Decimal | None) -> Decimal:
    """Wages still subject to a capped tax this period."""
    if wage_base is None:
        return base_wage
    remaining = max(Decimal("0"), wage_base - ytd)
    return min(base_wage, remaining)


def calculate(employee: Employee, hours: Decimal, schedule: str,
              ytd: Decimal, suta_rate: Decimal, rs: dict) -> dict:
    periods = periods_per_year(schedule)
    hours = money(hours or 0)
    rate = money(employee.pay_rate)

    if employee.pay_type == "hourly":
        gross = money(rate * hours)
    else:  # salary
        gross = money(rate / periods)

    versions = {}

    def ver(name, ruleset):
        versions[name] = (f"{ruleset.jurisdiction}/{ruleset.tax_type}/"
                          f"{ruleset.tax_year}v{ruleset.version}/{ruleset.status}") if ruleset else None

    # Social Security (employee + employer match), capped at wage base
    ss_rate = tr.get_num(rs["ss"], "rate", 0) if rs["ss"] else Decimal("0")
    ss_base = tr.get_num(rs["ss"], "wage_base") if rs["ss"] else None
    ss_wages = _capped(gross, ytd, ss_base)
    ss_ee = money(ss_wages * ss_rate)
    ss_er = ss_ee
    ver("ss", rs["ss"])

    # Medicare (no wage cap) + additional Medicare over threshold (employee only)
    med_rate = tr.get_num(rs["medicare"], "rate", 0) if rs["medicare"] else Decimal("0")
    med_ee = money(gross * med_rate)
    med_er = med_ee
    ver("medicare", rs["medicare"])
    if rs["addl_medicare"]:
        a_rate = tr.get_num(rs["addl_medicare"], "rate", 0)
        a_thr = tr.get_num(rs["addl_medicare"], "threshold", 0)
        over = max(Decimal("0"), (ytd + gross) - a_thr)
        addl = min(gross, over)
        med_ee += money(addl * a_rate)
        ver("addl_medicare", rs["addl_medicare"])

    # Federal withholding (annualized percentage method, simplified)
    fed_wh = Decimal("0")
    if rs["fed_wh"]:
        std = tr.get_json(rs["fed_wh"], "standard_deduction", {})
        brk = tr.get_json(rs["fed_wh"], "brackets", {})
        fs = employee.filing_status if employee.filing_status in brk else "single"
        annual = gross * periods
        taxable = max(Decimal("0"), annual - Decimal(str(std.get(fs, 0))))
        fed_wh = money(tr.bracket_tax(taxable, brk[fs]) / periods)
        ver("fed_wh", rs["fed_wh"])
    fed_wh = money(fed_wh + money(employee.fed_extra_withholding))

    # State (NJ) withholding (simplified)
    state_wh = Decimal("0")
    if rs["state_wh"]:
        brk = tr.get_json(rs["state_wh"], "brackets", {})
        band = brk.get("default") or next(iter(brk.values()), [])
        annual = gross * periods
        state_wh = money(tr.bracket_tax(annual, band) / periods)
        ver("state_wh", rs["state_wh"])
    state_wh = money(state_wh + money(employee.state_extra_withholding))

    # FUTA (employer) capped
    futa = Decimal("0")
    if rs["futa"]:
        f_rate = tr.get_num(rs["futa"], "rate", 0)
        f_base = tr.get_num(rs["futa"], "wage_base")
        futa = money(_capped(gross, ytd, f_base) * f_rate)
        ver("futa", rs["futa"])

    # SUTA (employer) — rate from employer setup, wage base from rules
    suta = Decimal("0")
    s_base = tr.get_num(rs["suta"], "wage_base") if rs["suta"] else None
    suta = money(_capped(gross, ytd, s_base) * money(suta_rate or 0))
    ver("suta", rs["suta"])

    net = money(gross - fed_wh - state_wh - ss_ee - med_ee)

    explanation = {
        "gross_pay": str(gross),
        "employee_taxes": {
            "federal_withholding": str(fed_wh), "state_withholding": str(state_wh),
            "social_security": str(ss_ee), "medicare": str(med_ee),
        },
        "employer_taxes": {
            "social_security": str(ss_er), "medicare": str(med_er),
            "futa": str(futa), "suta": str(suta),
        },
        "net_pay": str(net),
        "rule_versions": versions,
        "note": "Estimated from SAMPLE tax tables in DRAFT status. Review with your CPA.",
    }
    return {
        "gross_pay": gross, "fed_wh": fed_wh, "state_wh": state_wh,
        "ss_employee": ss_ee, "medicare_employee": med_ee,
        "ss_employer": ss_er, "medicare_employer": med_er,
        "futa": futa, "suta": suta, "net_pay": net,
        "explanation": explanation, "versions": versions,
    }
