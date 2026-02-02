from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import uuid
import os

from products.models import Product
from users.models import UserProfile
from sales.models import Customer


def invoice_pdf_path(instance, filename):
    """Generate unique path for invoice PDF files"""
    return f"invoices/{instance.shop_admin.id}/{instance.invoice_number}/{filename}"


class Invoice(models.Model):
    """Multitenant Invoice model with customer-level data isolation"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Unique invoice number with tenant prefix
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Multitenant fields - ensures data isolation
    shop_admin = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'SHOP_ADMIN'}, 
        related_name='invoices'
    )
    
    # Customer relationship with tenant validation
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='invoices'
    )
    
    # Invoice details
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Financial amounts with validation
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Tax rate in percentage"
    )
    tax_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)]
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    amount_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)]
    )
    
    # Additional fields
    notes = models.TextField(blank=True)
    payment_terms = models.TextField(
        blank=True, 
        default="Payment due within 30 days"
    )
    
    # Security and tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # PDF storage
    pdf_file = models.FileField(
        upload_to=invoice_pdf_path,
        blank=True,
        null=True
    )
    
    # Unique identifier for secure sharing
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    
    class Meta:
        app_label = 'invoicing'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop_admin', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate amounts
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Ensure decimal fields are not None
        if self.subtotal is None:
            self.subtotal = 0
        if self.tax_rate is None:
            self.tax_rate = 0
        if self.discount_amount is None:
            self.discount_amount = 0
        if self.amount_paid is None:
            self.amount_paid = 0
        
        # Calculate tax amount
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        
        # Calculate total
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Update status based on payment
        if self.amount_paid >= self.total_amount:
            self.status = 'PAID'
        elif self.amount_paid > 0:
            self.status = 'PARTIALLY_PAID'
        elif self.due_date < timezone.now().date() and self.status not in ['DRAFT', 'CANCELLED']:
            self.status = 'OVERDUE'
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number with tenant prefix"""
        prefix = f"INV-{self.shop_admin.id}"
        timestamp = timezone.now().strftime("%Y%m")
        # Get the latest invoice number for this shop and month
        latest = Invoice.objects.filter(
            shop_admin=self.shop_admin,
            invoice_number__startswith=f"{prefix}-{timestamp}"
        ).order_by('-invoice_number').first()
        
        if latest:
            last_number = int(latest.invoice_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}-{timestamp}-{new_number:04d}"
    
    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.balance_due > 0
    
    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.total_amount
    
    def get_absolute_url(self):
        return reverse('invoicing:invoice_detail', kwargs={'pk': self.pk})
    
    def get_public_url(self):
        """Get secure public URL for customer access"""
        return reverse('invoicing:public_invoice', kwargs={'uuid': self.uuid})
    
    def can_be_accessed_by(self, user):
        """Check if user can access this invoice (security check)"""
        if not user.is_authenticated:
            return False
        
        user_profile = user.profile
        
        # Site admin can access all
        if user_profile.is_site_admin:
            return True
        
        # Shop admin can access their own invoices
        if user_profile.is_shop_admin and self.shop_admin == user_profile:
            return True
        
        # Cashiers can access invoices from their shop
        if user_profile.is_cashier and self.shop_admin == user_profile.shop_admin:
            return True
        
        return False


class InvoiceItem(models.Model):
    """Invoice line items with tenant isolation"""
    
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE
    )
    description = models.CharField(
        max_length=200,
        help_text="Custom description (overrides product name if provided)"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    discount_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Discount rate in percentage"
    )
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'invoicing'
        unique_together = ['invoice', 'product']
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Use custom description or product name
        if not self.description:
            self.description = self.product.name
        
        # Calculate discount amount
        discount_amount = self.unit_price * (self.discount_rate / 100)
        discounted_price = self.unit_price - discount_amount
        
        # Calculate total
        self.total_price = self.quantity * discounted_price
        
        super().save(*args, **kwargs)
    
    @property
    def discount_amount(self):
        return self.unit_price * (self.discount_rate / 100)


class InvoicePayment(models.Model):
    """Payment records for invoices with tenant isolation"""
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('MOBILE', 'Mobile Money'),
        ('BANK', 'Bank Transfer'),
        ('CHECK', 'Check'),
        ('OTHER', 'Other'),
    ]
    
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)]
    )
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Transaction reference number"
    )
    notes = models.TextField(blank=True)
    
    # Security and tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoice_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'invoicing'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice', 'created_at']),
            models.Index(fields=['payment_method']),
        ]
    
    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update invoice amount paid
        self.invoice.amount_paid = InvoicePayment.objects.filter(
            invoice=self.invoice
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        self.invoice.save()


class InvoiceTemplate(models.Model):
    """Customizable invoice templates per tenant"""
    
    shop_admin = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'SHOP_ADMIN'},
        related_name='invoice_templates'
    )
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    
    # Template content
    header_text = models.TextField(
        blank=True,
        help_text="Custom header text for invoices"
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Custom footer text for invoices"
    )
    terms_conditions = models.TextField(
        blank=True,
        help_text="Terms and conditions"
    )
    
    # Styling options
    primary_color = models.CharField(
        max_length=7,
        default="#1f2937",
        help_text="Primary color in hex format"
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#6b7280",
        help_text="Secondary color in hex format"
    )
    
    # Logo
    logo = models.ImageField(
        upload_to='invoice_logos/',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'invoicing'
        ordering = ['name']
        unique_together = ['shop_admin', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.shop_admin.shop_name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per shop
        if self.is_default:
            InvoiceTemplate.objects.filter(
                shop_admin=self.shop_admin,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
