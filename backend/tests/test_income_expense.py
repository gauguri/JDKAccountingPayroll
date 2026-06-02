"""Income/expense preview + posting, and that nothing posts on preview."""
from decimal import Decimal

from tests.conftest import accounts_by_name


def test_income_preview_does_not_post(company, client):
    acc = accounts_by_name(client, company)
    body = {"date": "2026-03-01", "amount": "100.00", "payment_method": "cash",
            "income_account_id": acc["Sales Income"], "sales_tax_collected": "6.63"}
    pv = client.post(f"/api/companies/{company}/income/preview", json=body).json()
    assert "100" in pv["explanation"]
    # preview shows a balanced set of lines
    deb = sum(Decimal(l["debit"]) for l in pv["lines"])
    cred = sum(Decimal(l["credit"]) for l in pv["lines"])
    assert deb == cred == Decimal("106.63")
    # nothing recorded yet
    assert client.get(f"/api/companies/{company}/income").json() == []


def test_income_posts_and_books_sales_tax(company, client):
    acc = accounts_by_name(client, company)
    client.post(f"/api/companies/{company}/income", json={
        "date": "2026-03-01", "amount": "100.00", "payment_method": "check",
        "income_account_id": acc["Sales Income"], "sales_tax_collected": "6.63"})
    pnl = client.get(f"/api/companies/{company}/reports/pnl",
                     params={"from": "2026-01-01", "to": "2026-12-31"}).json()
    assert pnl["total_income"] == "100.00"
    bs = client.get(f"/api/companies/{company}/reports/balance_sheet").json()
    salestax = [l for l in bs["liabilities"] if l["account"] == "Sales Tax Payable"]
    assert salestax and salestax[0]["amount"] == "6.63"


def test_expense_on_credit_card(company, client):
    acc = accounts_by_name(client, company)
    r = client.post(f"/api/companies/{company}/expenses", json={
        "date": "2026-03-02", "amount": "40.00", "payment_method": "credit_card",
        "expense_account_id": acc["Supplies"], "cpa_review": True}).json()
    assert "Credit Card" in r["explanation"]
    bs = client.get(f"/api/companies/{company}/reports/balance_sheet").json()
    cc = [l for l in bs["liabilities"] if l["account"] == "Credit Card"]
    assert cc and cc[0]["amount"] == "40.00"
