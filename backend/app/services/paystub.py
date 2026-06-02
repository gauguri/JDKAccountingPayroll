"""Generate a pay stub PDF for one payroll item."""
import io


def paystub_pdf(*, company_name: str, employee_name: str, pay_date: str,
                period: str, item: dict, ytd: dict | None = None) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Pay Stub")
    s = getSampleStyleSheet()
    el = [
        Paragraph(company_name, s["Title"]),
        Paragraph("Pay Stub", s["Heading2"]),
        Paragraph(f"Employee: {employee_name}", s["Normal"]),
        Paragraph(f"Pay date: {pay_date} &nbsp;&nbsp; Period: {period}", s["Normal"]),
        Spacer(1, 12),
    ]
    rows = [
        ["Earnings", ""],
        ["Hours", item.get("hours", "")],
        ["Gross pay", f"${item['gross_pay']}"],
        ["", ""],
        ["Taxes withheld", ""],
        ["Federal income tax", f"${item['fed_wh']}"],
        ["State income tax (NJ)", f"${item['state_wh']}"],
        ["Social Security", f"${item['ss_employee']}"],
        ["Medicare", f"${item['medicare_employee']}"],
        ["", ""],
        ["Net pay", f"${item['net_pay']}"],
    ]
    t = Table(rows, colWidths=[260, 160], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (0, 4), "Helvetica-Bold"),
        ("FONTNAME", (0, 10), (-1, 10), "Helvetica-Bold"),
        ("LINEABOVE", (0, 10), (-1, 10), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)
    el.append(Spacer(1, 16))
    el.append(Paragraph(
        "<i>Estimated from sample tax tables under review. Not a tax filing. "
        "Confirm figures with your CPA.</i>", s["Normal"]))
    doc.build(el)
    return buf.getvalue()
