"""Render reports to CSV and simple PDF."""
import csv
import io


def report_to_rows(report: dict) -> list[list]:
    """Flatten a report dict into title + section rows for CSV/PDF."""
    rows: list[list] = []
    name = report.get("report", "Report")
    rows.append([name])
    for k in ("start", "end", "as_of"):
        if k in report:
            rows.append([k.replace("_", " ").title(), report[k]])
    rows.append([])

    def section(title, items, total_label=None, total_val=None):
        rows.append([title])
        for it in items:
            if "debit" in it or "credit" in it:
                rows.append([it.get("code", ""), it.get("account", ""),
                             str(it.get("debit", "")), str(it.get("credit", ""))])
            else:
                rows.append([it.get("account", ""), str(it.get("amount", ""))])
        if total_label is not None:
            rows.append([total_label, str(total_val)])
        rows.append([])

    if report["report"] == "Profit & Loss":
        section("Income", report["income"], "Total Income", report["total_income"])
        section("Expenses", report["expense"], "Total Expenses", report["total_expense"])
        rows.append(["Net Income", str(report["net_income"])])
    elif report["report"] == "Balance Sheet":
        section("Assets", report["assets"], "Total Assets", report["total_assets"])
        section("Liabilities", report["liabilities"], "Total Liabilities", report["total_liabilities"])
        section("Equity", report["equity"], "Total Equity", report["total_equity"])
    elif report["report"] == "Trial Balance":
        rows.append(["Code", "Account", "Debit", "Credit"])
        for r in report["rows"]:
            rows.append([r["code"], r["account"], str(r["debit"]), str(r["credit"])])
        rows.append(["", "TOTAL", str(report["total_debit"]), str(report["total_credit"])])
    elif report["report"] == "General Ledger":
        rows.append(["Date", "Account", "Memo", "Debit", "Credit"])
        for r in report["lines"]:
            rows.append([r["date"], r["account"], r["memo"] or "",
                         str(r["debit"]), str(r["credit"])])
    return rows


def to_csv(report: dict) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in report_to_rows(report):
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def to_pdf(report: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=report.get("report", "Report"))
    styles = getSampleStyleSheet()
    elements = [Paragraph(report.get("report", "Report"), styles["Title"])]
    if "explanation" in report:
        elements.append(Paragraph(report["explanation"], styles["Normal"]))
    elements.append(Spacer(1, 12))
    data = report_to_rows(report)
    data = [[str(c) for c in row] if row else [""] for row in data]
    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.grey),
    ]))
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()
