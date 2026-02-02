from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.template.loader import render_to_string
from django.conf import settings
import os


def generate_invoice_pdf(invoice, items, payments, template=None):
    """
    Generate PDF invoice using ReportLab
    Works on Windows without requiring system libraries
    """
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Get the story (content)
    story = []
    
    # Add company header
    story.append(_create_company_header(invoice, template))
    
    # Add invoice details
    story.append(Spacer(1, 12))
    story.append(_create_invoice_details(invoice))
    
    # Add billing and shipping info
    story.append(Spacer(1, 12))
    story.append(_create_billing_info(invoice))
    
    # Add items table
    story.append(Spacer(1, 12))
    story.append(_create_items_table(items))
    
    # Add totals
    story.append(Spacer(1, 12))
    story.append(_create_totals_section(invoice))
    
    # Add payment history if payments exist
    if payments:
        story.append(Spacer(1, 12))
        story.append(_create_payment_history(payments))
    
    # Add footer
    story.append(Spacer(1, 24))
    story.append(_create_footer(invoice, template))
    
    # Build the PDF
    doc.build(story)
    
    # Get the PDF value
    pdf_value = buffer.getvalue()
    buffer.close()
    
    return pdf_value


def _create_company_header(invoice, template):
    """Create company header section"""
    content = []
    
    # Company name
    company_name = template.header_text if template and template.header_text else invoice.shop_admin.shop_name
    content.append(Paragraph(company_name, getSampleStyleSheet()['Title']))
    
    # Company address
    address_parts = []
    if invoice.shop_admin.shop_address:
        address_parts.append(invoice.shop_admin.shop_address)
    if invoice.shop_admin.shop_city:
        address_parts.append(invoice.shop_admin.shop_city)
    if invoice.shop_admin.shop_phone:
        address_parts.append(f"Phone: {invoice.shop_admin.shop_phone}")
    if invoice.shop_admin.shop_email:
        address_parts.append(f"Email: {invoice.shop_admin.shop_email}")
    
    if address_parts:
        content.append(Paragraph(" | ".join(address_parts), getSampleStyleSheet()['Normal']))
    
    return content


def _create_invoice_details(invoice):
    """Create invoice details section"""
    content = []
    
    # Invoice number and date
    details = [
        f"Invoice Number: {invoice.invoice_number}",
        f"Issue Date: {invoice.issue_date.strftime('%B %d, %Y')}",
        f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}",
        f"Status: {invoice.get_status_display()}"
    ]
    
    for detail in details:
        content.append(Paragraph(detail, getSampleStyleSheet()['Normal']))
    
    return content


def _create_billing_info(invoice):
    """Create billing information section"""
    content = []
    
    # Bill to section
    content.append(Paragraph("Bill To:", getSampleStyleSheet()['Heading2']))
    content.append(Paragraph(invoice.customer.name, getSampleStyleSheet()['Heading3']))
    
    if invoice.customer.address:
        content.append(Paragraph(invoice.customer.address, getSampleStyleSheet()['Normal']))
    
    contact_info = []
    if invoice.customer.phone:
        contact_info.append(f"Phone: {invoice.customer.phone}")
    if invoice.customer.email:
        contact_info.append(f"Email: {invoice.customer.email}")
    
    if contact_info:
        content.append(Paragraph(" | ".join(contact_info), getSampleStyleSheet()['Normal']))
    
    return content


def _create_items_table(items):
    """Create items table"""
    content = []
    
    # Table headers
    headers = ['#', 'Description', 'Qty', 'Unit Price', 'Discount', 'Total']
    data = [headers]
    
    # Add items
    for i, item in enumerate(items, 1):
        row = [
            str(i),
            item.description,
            str(item.quantity),
            f"${item.unit_price:.2f}",
            f"{item.discount_rate:.0f}%" if item.discount_rate > 0 else "",
            f"${item.total_price:.2f}"
        ]
        data.append(row)
    
    # Create table
    table = Table(data, colWidths=[0.5*inch, 3*inch, 0.8*inch, 1*inch, 0.8*inch, 1*inch])
    
    # Add style to table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 1), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    
    content.append(table)
    return content


def _create_totals_section(invoice):
    """Create totals section"""
    content = []
    
    # Create totals data
    totals_data = [
        ['Subtotal:', f"${invoice.subtotal:.2f}"],
    ]
    
    if invoice.tax_amount > 0:
        totals_data.append([f'Tax ({invoice.tax_rate}%):', f"${invoice.tax_amount:.2f}"])
    
    if invoice.discount_amount > 0:
        totals_data.append(['Discount:', f"-${invoice.discount_amount:.2f}"])
    
    totals_data.append(['Total Amount:', f"${invoice.total_amount:.2f}"])
    
    if invoice.amount_paid > 0:
        totals_data.append(['Amount Paid:', f"${invoice.amount_paid:.2f}"])
        totals_data.append(['Balance Due:', f"${invoice.balance_due:.2f}"])
    else:
        totals_data.append(['Balance Due:', f"${invoice.balance_due:.2f}"])
    
    # Create table for totals
    totals_table = Table(totals_data, colWidths=[3*inch, 1.5*inch])
    
    # Style totals table
    totals_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('RIGHTPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (-1, -1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    totals_table.setStyle(totals_style)
    
    content.append(totals_table)
    return content


def _create_payment_history(payments):
    """Create payment history section"""
    content = []
    
    content.append(Paragraph("Payment History:", getSampleStyleSheet()['Heading2']))
    
    # Table headers
    headers = ['Date', 'Method', 'Amount', 'Transaction ID']
    data = [headers]
    
    # Add payments
    for payment in payments:
        row = [
            payment.created_at.strftime('%B %d, %Y'),
            payment.get_payment_method_display(),
            f"${payment.amount:.2f}",
            payment.transaction_id or '-'
        ]
        data.append(row)
    
    # Create table
    table = Table(data, colWidths=[1.5*inch, 1*inch, 1*inch, 1.5*inch])
    
    # Add style to table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 1), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    
    content.append(table)
    return content


def _create_footer(invoice, template):
    """Create footer section"""
    content = []
    
    # Payment terms
    payment_terms = template.payment_terms if template and template.payment_terms else invoice.payment_terms
    content.append(Paragraph(f"Payment Terms: {payment_terms}", getSampleStyleSheet()['Normal']))
    
    # Terms and conditions
    if template and template.terms_conditions:
        content.append(Spacer(1, 12))
        content.append(Paragraph("Terms and Conditions:", getSampleStyleSheet()['Heading3']))
        content.append(Paragraph(template.terms_conditions, getSampleStyleSheet()['Normal']))
    
    # Footer text
    if template and template.footer_text:
        content.append(Spacer(1, 12))
        content.append(Paragraph(template.footer_text, getSampleStyleSheet()['Normal']))
    
    # Standard footer
    content.append(Spacer(1, 24))
    content.append(Paragraph("This is a computer-generated invoice. No signature required.", getSampleStyleSheet()['Normal']))
    content.append(Paragraph(f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}", getSampleStyleSheet()['Normal']))
    
    return content
