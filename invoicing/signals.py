from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
from .models import Invoice, InvoiceItem, InvoicePayment


@receiver(pre_save, sender=Invoice)
def generate_invoice_number(sender, instance, **kwargs):
    """Generate unique invoice number before saving"""
    if not instance.invoice_number:
        instance.invoice_number = instance.generate_invoice_number()


@receiver(post_save, sender=InvoiceItem)
def update_invoice_totals_on_item_save(sender, instance, created, **kwargs):
    """Update invoice totals when items are added/updated"""
    if created or kwargs.get('update_fields'):
        invoice = instance.invoice
        # Recalculate subtotal from all items
        items_total = invoice.items.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        
        invoice.subtotal = items_total
        invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])


@receiver(post_save, sender=InvoicePayment)
def update_invoice_paid_amount(sender, instance, created, **kwargs):
    """Update invoice paid amount when payment is recorded"""
    if created:
        invoice = instance.invoice
        # Recalculate total paid amount
        total_paid = invoice.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        invoice.amount_paid = total_paid
        invoice.save(update_fields=['amount_paid'])


@receiver(pre_save, sender=Invoice)
def update_invoice_status(sender, instance, **kwargs):
    """Update invoice status based on payment and due date"""
    if instance.amount_paid >= instance.total_amount:
        instance.status = 'PAID'
    elif instance.amount_paid > 0:
        instance.status = 'PARTIALLY_PAID'
    elif instance.due_date < timezone.now().date() and instance.status not in ['DRAFT', 'CANCELLED']:
        instance.status = 'OVERDUE'
