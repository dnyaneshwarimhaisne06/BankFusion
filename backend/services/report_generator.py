import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any, List

class ReportGenerator:
    @staticmethod
    def generate_financial_report(data: Dict[str, Any], output_path: str) -> str:
        """
        Generate a PDF financial report aligned with frontend layout:
        - Title: Bank Statement Summary Report
        - Bank Details (bank, file, upload date)
        - Financial Summary table
        - Category Breakdown table
        - All Transactions table (multi-page)
        """
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = styles['Title']
        story.append(Paragraph("Bank Statement Summary Report", title_style))
        story.append(Spacer(1, 12))

        # Generated date centered
        normal_style = styles['Normal']
        date_str = datetime.now().strftime("%d %b %Y, %H:%M")
        center_style = ParagraphStyle('Center', parent=normal_style, alignment=1)
        story.append(Paragraph(f"Generated: {date_str}", center_style))
        story.append(Spacer(1, 16))

        # Bank Details
        story.append(Paragraph("Bank Details", styles['Heading2']))
        bd = data.get('bank_details', {})
        bank_details_table = Table(
            [
                ["Bank", bd.get('bank_name', 'Unknown')],
                ["File", bd.get('file_name', 'Untitled')],
                ["Uploaded", bd.get('upload_date', 'Unknown')],
                ["Account", bd.get('account_number', 'N/A')],
                ["Account Holder", bd.get('account_holder', 'N/A')],
            ],
            colWidths=[120, 360]
        )
        bank_details_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(bank_details_table)
        story.append(Spacer(1, 16))

        # Financial Summary
        story.append(Paragraph("Financial Summary", styles['Heading2']))
        fs = data.get('financial_summary', {})
        financial_table = Table(
            [
                ["Metric", "Amount (Rs.)"],
                ["Total Credit", f"{fs.get('total_credit', 0):,.2f}"],
                ["Total Debit", f"{fs.get('total_debit', 0):,.2f}"],
                ["Net Flow", f"{fs.get('net_flow', 0):,.2f}"],
                ["Final Balance", f"{abs(fs.get('final_balance', 0)):,.2f}"],
            ],
            colWidths=[240, 240]
        )
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.Color(59/255,130/255,246/255)),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(financial_table)
        story.append(Spacer(1, 16))

        # Category Breakdown
        story.append(Paragraph("Category Breakdown", styles['Heading2']))
        cb: List[Dict[str, Any]] = data.get('category_breakdown', [])
        cb_rows = [["Category", "Transactions", "Total Spending (Rs.)"]]
        for item in cb:
            cb_rows.append([item.get('category', 'Uncategorized'), str(item.get('count', 0)), f"{item.get('debit', 0):,.2f}"])
        category_table = Table(cb_rows, colWidths=[240, 120, 120])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.Color(59/255,130/255,246/255)),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(category_table)
        story.append(Spacer(1, 16))

        # All Transactions
        story.append(Paragraph("All Transactions", styles['Heading2']))
        txns: List[Dict[str, Any]] = data.get('transactions', [])
        txn_rows = [["Date", "Description", "Category", "Debit (Rs.)", "Credit (Rs.)", "Balance (Rs.)"]]
        for t in txns:
            txn_rows.append([
                str(t.get('date') or ''),
                str(t.get('description') or '')[:60],
                str(t.get('category') or ''),
                f"{float(t.get('debit', 0) or 0):,.2f}",
                f"{float(t.get('credit', 0) or 0):,.2f}",
                f"{abs(float(t.get('balance', 0) or 0)):,.2f}",
            ])
        txn_table = Table(txn_rows, colWidths=[70, 210, 80, 70, 70, 70], repeatRows=1)
        txn_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(txn_table)

        # Footer
        story.append(Spacer(1, 12))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray)
        story.append(Paragraph("This report was automatically generated by BankFusion Email Automation.", footer_style))

        doc.build(story)
        return output_path
