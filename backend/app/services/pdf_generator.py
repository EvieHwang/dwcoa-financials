"""PDF report generation using ReportLab."""

import io
from datetime import date
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.services import database, budget_calc
from app.routes import dues


def generate_dashboard_pdf(year: Optional[int] = None) -> bytes:
    """Generate a PDF report matching the dashboard layout.

    Args:
        year: Report year (defaults to current year)

    Returns:
        PDF content as bytes
    """
    if not year:
        current_year = database.get_config('current_year')
        year = int(current_year) if current_year else date.today().year

    # Get data
    accounts = budget_calc.get_account_balances()
    total_cash = sum(a['balance'] for a in accounts)
    budget_summary = budget_calc.get_budget_summary(year)
    dues_data = dues.get_dues_status(year)
    last_updated = database.get_config('last_upload_at')

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=6
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6
    )
    normal_style = styles['Normal']

    elements = []

    # Title
    elements.append(Paragraph("DWCOA Financial Dashboard", title_style))
    elements.append(Paragraph(f"Year: {year}", normal_style))
    if last_updated:
        elements.append(Paragraph(f"Last Updated: {last_updated}", normal_style))
    elements.append(Spacer(1, 12))

    # Account Balances
    elements.append(Paragraph("Account Balances", heading_style))
    account_data = [['Account', 'Balance']]
    for acc in accounts:
        account_data.append([acc['name'], format_currency(acc['balance'])])
    account_data.append(['Total Cash', format_currency(total_cash)])

    account_table = Table(account_data, colWidths=[3*inch, 2*inch])
    account_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 12))

    # Income Summary
    elements.append(Paragraph("Income Summary", heading_style))
    income = budget_summary['income_summary']
    income_data = [['Category', 'YTD Budget', 'YTD Actual']]
    for cat in income['categories']:
        income_data.append([
            cat['category'],
            format_currency(cat['ytd_budget']),
            format_currency(cat['ytd_actual'])
        ])
    income_data.append([
        'TOTAL',
        format_currency(income['ytd_budget']),
        format_currency(income['ytd_actual'])
    ])

    income_table = Table(income_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    income_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(income_table)
    elements.append(Spacer(1, 12))

    # Expense Summary
    elements.append(Paragraph("Expense Summary", heading_style))
    expense = budget_summary['expense_summary']
    expense_data = [['Category', 'YTD Budget', 'Actual', 'Remaining']]
    for cat in expense['categories']:
        expense_data.append([
            cat['category'],
            format_currency(cat['ytd_budget']),
            format_currency(cat['ytd_actual']),
            format_currency(cat['remaining'])
        ])
    expense_data.append([
        'TOTAL',
        format_currency(expense['ytd_budget']),
        format_currency(expense['ytd_actual']),
        format_currency(expense['remaining'])
    ])

    expense_table = Table(expense_data, colWidths=[2*inch, 1.25*inch, 1.25*inch, 1.25*inch])
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(expense_table)
    elements.append(Spacer(1, 12))

    # Dues Status
    elements.append(Paragraph("Dues Status by Unit", heading_style))
    dues_table_data = [['Unit', 'Ownership', 'Budget', 'Actual', 'Remaining']]
    for unit in dues_data['units']:
        dues_table_data.append([
            unit['unit'],
            f"{unit['ownership_pct']*100:.1f}%",
            format_currency(unit['expected_ytd']),
            format_currency(unit['paid_ytd']),
            format_currency(unit['outstanding'])
        ])

    dues_table = Table(dues_table_data, colWidths=[0.75*inch, 1*inch, 1.25*inch, 1.25*inch, 1.25*inch])
    dues_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(dues_table)

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "Denny Way Condo Owners Association",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey)
    ))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    return buffer.getvalue()


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"
