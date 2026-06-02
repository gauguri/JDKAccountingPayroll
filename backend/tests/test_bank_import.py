"""Bank CSV import: parsing, duplicate detection, mapping memory."""
import io

from tests.conftest import accounts_by_name  # noqa: F401


def _upload(client, company, csv_text, column_map, label="My Bank"):
    import json
    files = {"file": ("statement.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    data = {"bank_label": label, "column_map": json.dumps(column_map)}
    return client.post(f"/api/companies/{company}/bank/import", files=files, data=data)


def test_import_and_duplicate_detection(company, client):
    csv_text = ("Date,Description,Amount\n"
                "2026-05-01,DEPOSIT,500.00\n"
                "2026-05-02,SHELL FUEL,-45.00\n")
    cmap = {"date": "Date", "description": "Description", "amount": "Amount"}
    r1 = _upload(client, company, csv_text, cmap).json()
    assert r1["row_count"] == 2 and r1["duplicates"] == 0
    # fuel row should auto-suggest the Vehicle / Fuel account
    fuel = [t for t in r1["transactions"] if "SHELL" in t["description"]][0]
    assert fuel["direction"] == "debit" and fuel["suggested_account"] == "Vehicle / Fuel"
    # re-uploading the same file flags duplicates
    r2 = _upload(client, company, csv_text, cmap).json()
    assert r2["duplicates"] == 2


def test_mapping_remembered(company, client):
    csv_text = "Date,Description,Amount\n2026-06-01,Test,10.00\n"
    cmap = {"date": "Date", "description": "Description", "amount": "Amount"}
    _upload(client, company, csv_text, cmap, label="Chase")
    mappings = client.get(f"/api/companies/{company}/bank/mappings").json()
    assert any(m["bank_label"] == "Chase" for m in mappings)
