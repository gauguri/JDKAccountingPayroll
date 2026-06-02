"""Generate an ADP-style 'Earnings Statement' pay stub PDF for one payroll item."""
import io
from decimal import Decimal


def _m(v) -> str:
    return f"{Decimal(str(v)):,.2f}"


def paystub_pdf(*, company: dict, employee: dict, period_end: str, pay_date: str,
                rate: str | None, hours: str | None, pay_type: str,
                this_period: dict, ytd: dict) -> bytes:
    """ADP-style earnings statement.

    company: {name, address}
    employee: {name, ssn_masked, filing_status, address}
    this_period / ytd: dicts with gross_pay, fed_wh, state_wh, ss_employee,
        medicare_employee, ss_employer, medicare_employer, futa, suta, net_pay
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    small_b = ParagraphStyle("small_b", parent=small, fontName="Helvetica-Bold")
    title = ParagraphStyle("title", parent=styles["Normal"], fontSize=15,
                           fontName="Helvetica-Bold", alignment=2)  # right
    section = ParagraphStyle("section", parent=small_b, fontSize=9)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Earnings Statement",
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    el = []

    # ---- header: company info (left) | statement + employee (right) ----
    left_hdr = [
        Paragraph(company["name"], small_b),
        Paragraph((company.get("address") or "").replace("\n", "<br/>"), small),
        Spacer(1, 8),
        Paragraph(f"Social Security Number: {employee.get('ssn_masked') or '—'}", small),
        Paragraph(f"Taxable Marital Status: {employee.get('filing_status') or '—'}", small),
    ]
    right_hdr = [
        Paragraph("Earnings Statement", title),
        Spacer(1, 6),
        Paragraph(f"Period ending: {period_end}", small),
        Paragraph(f"Pay date: {pay_date}", small),
        Spacer(1, 8),
        Paragraph(employee["name"], small_b),
        Paragraph((employee.get("address") or "").replace("\n", "<br/>"), small),
    ]
    hdr = Table([[left_hdr, right_hdr]], colWidths=[3.6 * inch, 3.6 * inch])
    hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el.append(hdr)
    el.append(Spacer(1, 10))

    # ---- earnings table ----
    earn = [
        ["Earnings", "rate", "hours", "this period", "year to date"],
        ["Regular",
         _m(rate) if (pay_type == "hourly" and rate) else "",
         hours if (pay_type == "hourly" and hours) else "",
         _m(this_period["gross_pay"]), _m(ytd["gross_pay"])],
        ["Gross Pay", "", "", "$ " + _m(this_period["gross_pay"]), _m(ytd["gross_pay"])],
    ]
    t_earn = Table(earn, colWidths=[1.25 * inch, 0.6 * inch, 0.5 * inch, 1.0 * inch, 1.0 * inch])
    t_earn.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # ---- statutory deductions ----
    ded = [
        ["Deductions", "Statutory", "this period", "year to date"],
        ["", "Federal Income Tax", "- " + _m(this_period["fed_wh"]), _m(ytd["fed_wh"])],
        ["", "Social Security Tax", "- " + _m(this_period["ss_employee"]), _m(ytd["ss_employee"])],
        ["", "Medicare Tax", "- " + _m(this_period["medicare_employee"]), _m(ytd["medicare_employee"])],
        ["", "NJ State Income Tax", "- " + _m(this_period["state_wh"]), _m(ytd["state_wh"])],
        ["Net Pay", "", "$ " + _m(this_period["net_pay"]), ""],
    ]
    t_ded = Table(ded, colWidths=[0.85 * inch, 1.5 * inch, 1.0 * inch, 1.0 * inch])
    t_ded.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEABOVE", (0, 5), (-1, 5), 0.5, colors.black),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # ---- right column: employer taxes + notes ----
    emp = [
        ["Employer Taxes", "this period", "total to date"],
        ["Social Security", _m(this_period["ss_employer"]), _m(ytd["ss_employer"])],
        ["Medicare", _m(this_period["medicare_employer"]), _m(ytd["medicare_employer"])],
        ["FUTA", _m(this_period["futa"]), _m(ytd["futa"])],
        ["SUTA (NJ)", _m(this_period["suta"]), _m(ytd["suta"])],
    ]
    t_emp = Table(emp, colWidths=[1.1 * inch, 0.85 * inch, 0.85 * inch])
    t_emp.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    notes = [
        Paragraph("Important Notes", section),
        Paragraph("These amounts are <b>estimated from sample tax tables that are "
                  "still in draft</b> and have not been approved. This statement is "
                  "for records only — it is not a paycheck and not a tax filing. "
                  "Confirm all figures with your CPA before paying.", small),
    ]

    left_col = [t_earn, Spacer(1, 12), t_ded]
    right_col = [t_emp, Spacer(1, 12)] + notes
    body = Table([[left_col, right_col]], colWidths=[4.45 * inch, 2.8 * inch])
    body.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el.append(body)
    el.append(Spacer(1, 16))
    el.append(Paragraph("Employer taxes (Social Security, Medicare, FUTA, SUTA) are "
                        "paid by the company and are shown for information only — they "
                        "are not withheld from your pay.", small))

    doc.build(el)
    return buf.getvalue()
