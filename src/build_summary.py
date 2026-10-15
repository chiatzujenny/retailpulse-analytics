"""Create a one-page executive summary from the validated educational case."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from retail_analytics import load_data, compute_summary, build_tables


def main():
    root = Path(__file__).resolve().parents[1]
    tx, customers, audit = load_data(root / "data")
    kpi = compute_summary(tx)
    tables, _ = build_tables(tx, customers)
    cardinal, tint, gray = colors.HexColor("#990000"), colors.HexColor("#FFF2BF"), colors.HexColor("#555555")
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=gray)
    section = ParagraphStyle("section", parent=body, fontName="Helvetica-Bold", fontSize=10.5, textColor=cardinal, spaceBefore=10, spaceAfter=7)
    title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=cardinal)
    story = [Paragraph("RetailPulse | Executive Summary", title), Paragraph("Retail Sales &amp; Customer Analytics - 2023 observation window", body), Paragraph("USC MS Business Analytics pre-program team case | Portfolio adaptation by Jenny Tsai", small), Spacer(1, 11)]
    metrics = [
        ["Recorded revenue (USD)", "Transactions", "Purchasers / registered", "Return rate"],
        [f"{kpi['revenue_after_discount']:,.2f}", str(kpi["transactions"]), f"{kpi['purchasing_customers']} / {len(customers)}", f"{kpi['return_rate']:.1%}"],
    ]
    table = Table(metrics, colWidths=[151, 90, 157, 118])
    table.setStyle(TableStyle([("FONTNAME", (0,0), (-1,0), "Helvetica"), ("FONTSIZE", (0,0), (-1,0), 8), ("TEXTCOLOR", (0,0), (-1,0), gray), ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold"), ("FONTSIZE", (0,1), (-1,1), 16), ("TEXTCOLOR", (0,1), (-1,1), cardinal), ("BACKGROUND", (0,0), (-1,-1), tint), ("TOPPADDING", (0,0), (-1,0), 9), ("BOTTOMPADDING", (0,1), (-1,1), 11)]))
    story += [table, Paragraph("Findings and proposed investigations", section)]
    findings = [
        ("Product concentration", "Laptops contribute 34.8% of recorded revenue (58,101.12 USD) across 12 of 150 transactions. Review product-level returns and costs before drawing profitability conclusions."),
        ("East: review return records", "East has 9 returns in 46 transactions (19.6%), versus 10 in the other 104 transactions (9.6%). Audit these nine records and compare product and payment mix before assigning a cause."),
        ("West: investigate volume and coverage", "West records 26 transactions and the lowest regional revenue. Its average transaction value of 1,101.17 USD is close to the overall 1,112.73 USD; its return rate is below the overall rate. Check traffic, conversion and sampling coverage."),
        ("Customer prioritization", "C051 has the highest heuristic RFM score (15). Revenue tiering and RFM describe different customer attributes; these scores do not predict churn or lifetime value."),
    ]
    for label, text in findings:
        story.append(Paragraph(f"<b>{label}.</b> {text}", body))
    story.append(Paragraph("Regional operating view", section))
    rows = [["Region", "Revenue (USD)", "Transactions", "Avg. value (USD)", "Returns", "Return rate"]]
    for row in tables["region_summary"].itertuples():
        rows.append([row.region, f"{row.revenue:,.2f}", str(row.transaction_count), f"{row.average_transaction_value:,.2f}", str(row.return_count), f"{row.return_rate:.1%}"])
    rows.append(["Total", f"{kpi['revenue_after_discount']:,.2f}", "150", f"{kpi['average_transaction_value']:,.2f}", "19", f"{kpi['return_rate']:.1%}"])
    table = Table(rows, colWidths=[62, 100, 84, 108, 60, 102], repeatRows=1)
    table.setStyle(TableStyle([("FONTNAME", (0,0), (-1,0), "Helvetica-BoldOblique"), ("TEXTCOLOR", (0,0), (-1,0), cardinal), ("FONTNAME", (0,1), (-1,-1), "Helvetica"), ("FONTSIZE", (0,0), (-1,-1), 8.5), ("ALIGN", (1,0), (-1,-1), "RIGHT"), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6), ("LINEBELOW", (0,0), (-1,0), .7, colors.black), ("LINEABOVE", (0,-1), (-1,-1), .7, colors.black), ("BACKGROUND", (0,-1), (-1,-1), tint), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold")]))
    story += [table, Paragraph("Data quality and decision limits", section)]
    story.append(Paragraph("Five discounts and eight ratings are missing. Four revenue-formula exceptions, all involving missing discounts, total -261.77 USD under a 0% fill; source revenue is retained and unknown discounts are shown separately. Nine transactions predate loyalty signup and remain flagged. All 150 transactions match the 60-customer Week 5 master.", small))
    story.append(Paragraph("Revenue is after discount; refund treatment and costs are unknown. Rating comparisons use observed responses. Discount differences are observational, one year does not establish recurring seasonality, and sparse payment groups with repeated customers do not support a standalone significance claim. Recommendations are proposed investigations; no business impact is claimed.", small))
    story.append(Spacer(1, 6))
    story.append(Paragraph('<link href="https://github.com/chiatzujenny/retailpulse-analytics" color="#990000">github.com/chiatzujenny/retailpulse-analytics</link> | Python, Pandas, NumPy, Matplotlib', small))
    destination = root / "outputs" / "executive_summary.pdf"
    doc = SimpleDocTemplate(str(destination), pagesize=letter, rightMargin=48, leftMargin=48, topMargin=38, bottomMargin=34, title="RetailPulse Executive Summary", author="Jenny Tsai")
    doc.build(story)
    print(f"Created {destination.name}")


if __name__ == "__main__":
    main()
