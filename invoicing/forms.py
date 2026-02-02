from django import forms
from django.forms import formset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Invoice, InvoiceItem, InvoicePayment, InvoiceTemplate
from sales.models import Customer
from products.models import Product


class InvoiceForm(forms.ModelForm):
    """Form for creating/editing invoices with tenant validation"""
    
    class Meta:
        model = Invoice
        fields = [
            'customer', 'issue_date', 'due_date', 'tax_rate', 
            'discount_amount', 'notes', 'payment_terms'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100', 'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'payment_terms': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter customers based on user permissions
        if self.user:
            profile = self.user.profile
            if profile.is_site_admin:
                customers = Customer.objects.all()
            elif profile.is_shop_admin:
                customers = Customer.objects.filter(shop_admin=profile)
            elif profile.is_cashier:
                customers = Customer.objects.filter(shop_admin=profile.shop_admin)
            else:
                customers = Customer.objects.none()
            
            self.fields['customer'].queryset = customers
            self.fields['customer'].widget.attrs.update({'class': 'form-control'})
        
        # Set default dates
        if not self.instance.pk:
            self.fields['issue_date'].initial = timezone.now().date()
            self.fields['due_date'].initial = timezone.now().date() + timezone.timedelta(days=30)
            # Set default values for decimal fields
            self.fields['tax_rate'].initial = 0
            self.fields['discount_amount'].initial = 0
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        issue_date = self.cleaned_data.get('issue_date')
        
        if due_date and issue_date and due_date < issue_date:
            raise ValidationError("Due date cannot be before issue date.")
        
        return due_date
    
    def clean_tax_rate(self):
        tax_rate = self.cleaned_data.get('tax_rate')
        if tax_rate and tax_rate < 0:
            raise ValidationError("Tax rate cannot be negative.")
        return tax_rate
    
    def clean_discount_amount(self):
        discount_amount = self.cleaned_data.get('discount_amount')
        if discount_amount and discount_amount < 0:
            raise ValidationError("Discount amount cannot be negative.")
        return discount_amount


class InvoiceItemForm(forms.ModelForm):
    """Form for adding items to invoices"""
    
    class Meta:
        model = InvoiceItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_rate']
        widgets = {
            'quantity': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'discount_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values
        if not self.instance.pk:
            self.fields['quantity'].initial = 1
            self.fields['discount_rate'].initial = 0
        
        # Add CSS classes
        self.fields['product'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")
        return unit_price
    
    def clean_discount_rate(self):
        discount_rate = self.cleaned_data.get('discount_rate')
        if discount_rate and (discount_rate < 0 or discount_rate > 100):
            raise ValidationError("Discount rate must be between 0 and 100.")
        return discount_rate


class InvoicePaymentForm(forms.ModelForm):
    """Form for recording invoice payments"""
    
    class Meta:
        model = InvoicePayment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS class to payment method
        self.fields['payment_method'].widget.attrs.update({'class': 'form-control'})
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Payment amount must be greater than 0.")
        
        if self.invoice and amount:
            balance_due = self.invoice.balance_due
            if amount > balance_due:
                raise ValidationError(f"Payment amount cannot exceed balance due of {balance_due:.2f}")
        
        return amount


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices"""
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Invoice.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        required=False,
        empty_label="All Customers",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by invoice number or customer...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter customers based on user permissions
        if self.user:
            profile = self.user.profile
            if profile.is_site_admin:
                customers = Customer.objects.all()
            elif profile.is_shop_admin:
                customers = Customer.objects.filter(shop_admin=profile)
            elif profile.is_cashier:
                customers = Customer.objects.filter(shop_admin=profile.shop_admin)
            else:
                customers = Customer.objects.none()
            
            self.fields['customer'].queryset = customers
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Date from cannot be after date to.")
        
        return cleaned_data


class InvoiceTemplateForm(forms.ModelForm):
    """Form for creating/editing invoice templates"""
    
    class Meta:
        model = InvoiceTemplate
        fields = [
            'name', 'is_default', 'header_text', 'footer_text', 
            'terms_conditions', 'primary_color', 'secondary_color', 'logo'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'header_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'footer_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'terms_conditions': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_primary_color(self):
        color = self.cleaned_data.get('primary_color')
        if color and not color.startswith('#'):
            raise ValidationError("Color must be in hex format (e.g., #1f2937).")
        return color
    
    def clean_secondary_color(self):
        color = self.cleaned_data.get('secondary_color')
        if color and not color.startswith('#'):
            raise ValidationError("Color must be in hex format (e.g., #6b7280).")
        return color


# Formsets for invoice items
InvoiceItemFormSet = formset_factory(
    InvoiceItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)
