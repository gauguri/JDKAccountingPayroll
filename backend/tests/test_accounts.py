"""Chart of accounts: preload, guards, suggestions."""
from tests.conftest import accounts_by_name


def test_chart_preloaded(company, client):
    names = accounts_by_name(client, company)
    for expected in ("Sales Income", "Blank Shirts / Hats", "Vinyl / Sign Materials",
                     "Checking Account", "Sales Tax Payable", "Owner Draws"):
        assert expected in names


def test_cannot_delete_system_account(company, client):
    acc = accounts_by_name(client, company)
    r = client.delete(f"/api/companies/{company}/accounts/{acc['Sales Income']}")
    assert r.status_code == 400
    assert "hide" in r.json()["detail"].lower()


def test_cannot_delete_account_with_transactions(company, client):
    acc = accounts_by_name(client, company)
    # add a custom account, post an expense to it, then deletion must be blocked
    new = client.post(f"/api/companies/{company}/accounts", json={
        "name": "Custom Expense", "type": "expense"}).json()
    client.post(f"/api/companies/{company}/expenses", json={
        "date": "2026-01-10", "amount": "25.00", "payment_method": "cash",
        "expense_account_id": new["id"]})
    r = client.delete(f"/api/companies/{company}/accounts/{new['id']}")
    assert r.status_code == 400


def test_hide_account(company, client):
    acc = accounts_by_name(client, company)
    r = client.post(f"/api/companies/{company}/accounts/{acc['Miscellaneous']}/hide")
    assert r.status_code == 200 and r.json()["hidden"] is True


def test_suggest_account(company, client):
    r = client.get(f"/api/companies/{company}/accounts/suggest", params={"desc": "SHELL FUEL #123"})
    assert r.json()["account_name"] == "Vehicle / Fuel"
