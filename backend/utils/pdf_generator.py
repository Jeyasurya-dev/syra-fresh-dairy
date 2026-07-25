"""
SYRA Fresh - Salary Slip PDF Generator

Generates an actual PDF file (not just a printable HTML page) for a salary
transaction, using reportlab - a pure-Python library with no system
dependencies, so it installs cleanly anywhere `pip install -r
requirements.txt` runs. Mirrors the same data shown on
frontend/admin/salary-slip.html, so the on-screen slip and the downloaded
PDF always agree.
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

FOREST_GREEN = colors.HexColor("#2D6A4F")
INK_SOFT = colors.HexColor("#6B7568")
LIGHT_BG = colors.HexColor("#F1F3EC")


def generate_salary_slip_pdf(transaction):
    """transaction: the raw MongoDB document (or serialize_salary_transaction()
    output - both have the same field names used below) for one salary slip.
    Returns a BytesIO positioned at 0, ready to send as a file."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SlipTitle", fontSize=18, textColor=FOREST_GREEN, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SlipMeta", fontSize=9, textColor=INK_SOFT, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="SectionHeading", fontSize=10, textColor=INK_SOFT, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="SlipBody", fontSize=10))

    b = transaction["breakdown"]
    status = transaction.get("status", "pending")
    role_label = "Hub Manager" if transaction.get("person_type") == "hub_manager" else "Delivery Boy"

    story = []

    # Header: logo/title on the left, slip meta on the right
    header_table = Table([[
        Paragraph("SYRA Fresh<br/><font size=9 color='#6B7568'>Salary Slip</font>", styles["SlipTitle"]),
        Paragraph(
            f"Slip #{transaction.get('slip_number')}<br/>"
            f"Month: {transaction.get('month')}<br/>"
            f"<b><font color='{'#155724' if status == 'paid' else '#856404'}'>"
            f"{'PAID' if status == 'paid' else 'PENDING'}</font></b>",
            styles["SlipMeta"],
        ),
    ]], colWidths=[100 * mm, 72 * mm])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(Table([[""]], colWidths=[172 * mm], rowHeights=[1.2],
                        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), FOREST_GREEN)])))
    story.append(Spacer(1, 10))

    # Employee section
    story.append(Paragraph("EMPLOYEE", styles["SectionHeading"]))
    story.append(Paragraph(
        f"<b>{transaction.get('person_name')}</b> &nbsp;&bull;&nbsp; {role_label}<br/>"
        f"Hub: {transaction.get('hub_name') or '—'}",
        styles["SlipBody"],
    ))

    # Attendance section
    story.append(Paragraph("ATTENDANCE THIS MONTH", styles["SectionHeading"]))
    att_cells = [f"Present: {b.get('attendance_present_days', 0)} day(s)",
                 f"Half Day: {b.get('attendance_half_days', 0)} day(s)",
                 f"Absent: {b.get('attendance_absent_days', 0)} day(s)"]
    if "orders_delivered" in b:
        att_cells.append(f"Orders Delivered: {b.get('orders_delivered', 0)}")
    story.append(Paragraph(" &nbsp;&bull;&nbsp; ".join(att_cells), styles["SlipBody"]))

    # Earnings table
    story.append(Paragraph("EARNINGS", styles["SectionHeading"]))
    earnings_rows = [
        ["Monthly Salary", f"Rs. {b.get('monthly_salary', 0):.2f}"],
        [f"Per-Order Incentive ({b.get('orders_delivered', 0)} x Rs. {b.get('per_order_incentive_rate', 0)})",
         f"Rs. {b.get('per_order_incentive_total', 0):.2f}"],
        ["Fuel Allowance", f"Rs. {b.get('fuel_allowance', 0):.2f}"],
        ["Bonus", f"Rs. {b.get('bonus', 0):.2f}"],
        ["Gross Earnings", f"Rs. {transaction.get('gross_earnings', 0):.2f}"],
    ]
    story.append(_money_table(earnings_rows, bold_last_row=True))

    # Deductions table
    story.append(Paragraph("DEDUCTIONS", styles["SectionHeading"]))
    fine_label = "Fine"
    if b.get("fine_reason"):
        fine_label += f" ({b['fine_reason']})"
    deduction_rows = [
        ["Attendance Deduction (absences / half-days)", f"- Rs. {b.get('attendance_deduction', 0):.2f}"],
        ["Other Deductions", f"- Rs. {b.get('other_deductions', 0):.2f}"],
        [fine_label, f"- Rs. {b.get('fine', 0):.2f}"],
        ["Total Deductions", f"- Rs. {transaction.get('total_deductions', 0):.2f}"],
    ]
    story.append(_money_table(deduction_rows, bold_last_row=True))

    # Net pay
    story.append(Spacer(1, 8))
    net_table = Table([["NET PAY", f"Rs. {transaction.get('net_pay', 0):.2f}"]], colWidths=[120 * mm, 52 * mm])
    net_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("TEXTCOLOR", (0, 0), (-1, -1), FOREST_GREEN),
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, FOREST_GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(net_table)

    if status == "paid" and transaction.get("paid_at"):
        paid_at = transaction["paid_at"]
        paid_at_str = paid_at.strftime("%d %b %Y") if hasattr(paid_at, "strftime") else str(paid_at)[:10]
        ref = transaction.get("payment_reference")
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"Paid on {paid_at_str}" + (f" &mdash; Ref: {ref}" if ref else ""),
            ParagraphStyle(name="PaidNote", fontSize=9, textColor=INK_SOFT),
        ))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This is a system-generated salary slip from SYRA Fresh.",
        ParagraphStyle(name="Footer", fontSize=8, textColor=INK_SOFT, alignment=TA_CENTER),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _money_table(rows, bold_last_row=False):
    table = Table(rows, colWidths=[120 * mm, 52 * mm])
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LIGHT_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if bold_last_row:
        style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
        style.append(("LINEABOVE", (0, -1), (-1, -1), 0.8, FOREST_GREEN))
    table.setStyle(TableStyle(style))
    return table
