"""Payroll: tax-rule seed, employees, run calculation, posting, stubs, reports."""
from decimal import Decimal

from tests.conftest import accounts_by_name


def test_sample_tax_rules_seeded_as_draft(company, client):
    rows = client.get("/api/tax-rules").json()
    kinds = {(r["jurisdiction"], r["tax_type"]) for r in rows}
    assert ("US", "ss") in kinds and ("US", "medicare") in kinds
    assert ("US", "futa") in kinds and ("NJ", "suta") in kinds
    # everything ships as draft (must be approved before real use)
    assert all(r["status"] == "draft" for r in rows)


def test_approve_ruleset(company, client):
    rs = client.get("/api/tax-rules").json()[0]
    r = client.post(f"/api/tax-rules/{rs['id']}/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"


def _employee(client, company, rate="20", pay_type="hourly"):
    return client.post(f"/api/companies/{company}/payroll/employees", json={
        "first_name": "Pat", "last_name": "Smith", "ssn": "123-45-6789",
        "pay_type": pay_type, "pay_rate": rate, "filing_status": "single",
    }).json()


def test_employee_ssn_is_masked(company, client):
    e = _employee(client, company)
    assert e["ssn_masked"] and e["ssn_masked"].endswith("6789")
    assert "123-45" not in e["ssn_masked"]


def _run_biweekly_payroll(company, client) -> dict:
    """Helper: set up + run an 80-hour biweekly payroll for one $20/hr employee.

    Returns the calculated run. (Helper, not a test — so it may return a value.)
    """
    client.put(f"/api/companies/{company}/payroll/setup",
               json={"payroll_schedule": "biweekly", "suta_rate": "0.02"})
    emp = _employee(client, company, rate="20")
    return client.post(f"/api/companies/{company}/payroll/runs", json={
        "pay_period_start": "2026-01-01", "pay_period_end": "2026-01-14",
        "pay_date": "2026-01-16",
        "hours": [{"employee_id": emp["id"], "hours": "80"}],
    }).json()


def test_payroll_run_calculates_and_net_is_consistent(company, client):
    run = _run_biweekly_payroll(company, client)
    assert run["status"] == "calculated"
    it = run["items"][0]
    gross = Decimal(it["gross_pay"])
    assert gross == Decimal("1600.00")  # 20 * 80
    taxes = (Decimal(it["fed_wh"]) + Decimal(it["state_wh"])
             + Decimal(it["ss_employee"]) + Decimal(it["medicare_employee"]))
    assert Decimal(it["net_pay"]) == gross - taxes
    # SS = 6.2%, Medicare = 1.45%
    assert Decimal(it["ss_employee"]) == Decimal("99.20")
    assert Decimal(it["medicare_employee"]) == Decimal("23.20")


def test_posting_keeps_books_balanced(company, client):
    run = _run_biweekly_payroll(company, client)
    posted = client.post(f"/api/companies/{company}/payroll/runs/{run['id']}/post").json()
    assert "journal_entry_id" in posted
    tb = client.get(f"/api/companies/{company}/reports/trial_balance").json()
    assert tb["balances"] is True
    bs = client.get(f"/api/companies/{company}/reports/balance_sheet").json()
    assert bs["balances"] is True


def test_pay_stub_pdf(company, client):
    run = _run_biweekly_payroll(company, client)
    item_id = run["items"][0]["id"]
    r = client.get(f"/api/companies/{company}/payroll/runs/{run['id']}/stubs/{item_id}")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_payroll_tax_liability_report(company, client):
    run = _run_biweekly_payroll(company, client)
    client.post(f"/api/companies/{company}/payroll/runs/{run['id']}/post")
    rep = client.get(f"/api/companies/{company}/payroll/reports/tax_liability").json()
    assert "federal_941_liability" in rep and "state_unemployment_suta" in rep
