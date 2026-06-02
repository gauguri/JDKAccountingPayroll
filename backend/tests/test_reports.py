"""Reports must tie out: trial balance balances, A = L + E."""
from decimal import Decimal

from tests.conftest import accounts_by_name


def _seed(client, company):
    acc = accounts_by_name(client, company)
    client.post(f"/api/companies/{company}/income", json={
        "date": "2026-04-01", "amount": "1000.00", "payment_method": "ach",
        "income_account_id": acc["Sales Income"], "sales_tax_collected": "66.25"})
    client.post(f"/api/companies/{company}/expenses", json={
        "date": "2026-04-03", "amount": "250.00", "payment_method": "check",
        "expense_account_id": acc["Blank Shirts / Hats"]})
    client.post(f"/api/companies/{company}/expenses", json={
        "date": "2026-04-05", "amount": "120.00", "payment_method": "credit_card",
        "expense_account_id": acc["Advertising"]})


def test_trial_balance_balances(company, client):
    _seed(client, company)
    tb = client.get(f"/api/companies/{company}/reports/trial_balance").json()
    assert tb["balances"] is True
    assert tb["total_debit"] == tb["total_credit"]


def test_balance_sheet_balances(company, client):
    _seed(client, company)
    bs = client.get(f"/api/companies/{company}/reports/balance_sheet").json()
    assert bs["balances"] is True
    assert Decimal(bs["total_assets"]) == Decimal(bs["total_liabilities"]) + Decimal(bs["total_equity"])


def test_pnl_net_income(company, client):
    _seed(client, company)
    pnl = client.get(f"/api/companies/{company}/reports/pnl",
                     params={"from": "2026-01-01", "to": "2026-12-31"}).json()
    # income 1000 - (250 + 120) = 630
    assert pnl["net_income"] == "630.00"


def test_csv_and_pdf_export(company, client):
    _seed(client, company)
    csv = client.get(f"/api/companies/{company}/reports/pnl", params={"format": "csv"})
    assert csv.status_code == 200 and b"Net Income" in csv.content
    pdf = client.get(f"/api/companies/{company}/reports/balance_sheet", params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_cpa_export_zip(company, client):
    _seed(client, company)
    r = client.post(f"/api/companies/{company}/cpa-export")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # zip magic
