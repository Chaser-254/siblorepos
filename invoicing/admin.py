from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Invoice, InvoiceItem, InvoicePayment, InvoiceTemplate


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ('total_price',)
    fields = ('product', 'description', 'quantity', 'unit_price', 'discount_rate', 'total_price')


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 1
    readonly_fields = ('created_at',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer', 'shop_admin', 'status', 
        'total_amount', 'amount_paid', 'balance_due', 'due_date', 
        'created_at', 'invoice_actions'
    ]
    list_filter = ['status', 'shop_admin', 'created_at', 'due_date']
    search_fields = ['invoice_number', 'customer__name', 'customer__email']
    readonly_fields = ['invoice_number', 'uuid', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline, InvoicePaymentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_number', 'shop_admin', 'customer', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'created_at', 'updated_at')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid')
        }),
        ('Additional Information', {
            'fields': ('notes', 'payment_terms', 'uuid', 'pdf_file')
        }),
    )
    
    def balance_due(self, obj):
        return obj.total_amount - obj.amount_paid
    balance_due.short_description = 'Balance Due'
    
    def invoice_actions(self, obj):
        """Custom action buttons"""
        actions = []
        
        # View detail link
        detail_url = reverse('admin:invoicing_invoice_change', args=[obj.pk])
        actions.append(f'<a href="{detail_url}" class="button">View</a>')
        
        # PDF link if available
        if obj.pdf_file:
            pdf_url = obj.pdf_file.url
            actions.append(f'<a href="{pdf_url}" target="_blank" class="button">PDF</a>')
        
        # Public link
        public_url = reverse('invoicing:public_invoice', args=[obj.uuid])
        actions.append(f'<a href="{public_url}" target="_blank" class="button">Public Link</a>')
        
        return format_html(' '.join(actions))
    invoice_actions.short_description = 'Actions'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter by user's shop if not superuser
        return qs.filter(shop_admin=request.user.profile)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            if obj.status not in ['DRAFT']:
                return ['invoice_number', 'customer', 'shop_admin', 'status', 'uuid', 'created_at', 'updated_at']
        return self.readonly_fields


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'description', 'quantity', 'unit_price', 'total_price']
    list_filter = ['invoice__status', 'created_at']
    search_fields = ['invoice__invoice_number', 'product__name', 'description']
    readonly_fields = ['total_price', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(invoice__shop_admin=request.user.profile)


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'transaction_id', 'created_by', 'created_at']
    list_filter = ['payment_method', 'created_at']
    search_fields = ['invoice__invoice_number', 'transaction_id', 'notes']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(invoice__shop_admin=request.user.profile)


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop_admin', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'shop_admin__shop_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'shop_admin', 'is_default')
        }),
        ('Template Content', {
            'fields': ('header_text', 'footer_text', 'terms_conditions')
        }),
        ('Styling', {
            'fields': ('primary_color', 'secondary_color', 'logo')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(shop_admin=request.user.profile)
