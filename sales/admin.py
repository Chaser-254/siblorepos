from django.contrib import admin
from .models import Customer, Sale, SaleItem, Debt, DebtPayment, Revenue

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'total_debt', 'available_credit', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering = ['name']
    readonly_fields = ['total_debt', 'available_credit', 'created_at']
    
    def total_debt(self, obj):
        return obj.total_debt
    total_debt.short_description = 'Total Debt'
    
    def available_credit(self, obj):
        return obj.available_credit
    available_credit.short_description = 'Available Credit'

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'payment_method', 'status', 'total_amount', 'amount_paid', 'balance_due', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['invoice_number', 'customer__name']
    ordering = ['-created_at']
    readonly_fields = ['invoice_number', 'balance_due', 'is_fully_paid', 'profit', 'created_at', 'updated_at']

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__created_at']
    search_fields = ['product__name', 'sale__invoice_number']
    ordering = ['-created_at']

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['customer', 'sale', 'amount', 'amount_paid', 'balance', 'status', 'due_date', 'created_at']
    list_filter = ['status', 'due_date']
    search_fields = ['customer__name', 'sale__invoice_number']
    ordering = ['-created_at']
    readonly_fields = ['balance', 'created_at', 'updated_at']

@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ['debt', 'amount', 'payment_method', 'created_by', 'created_at']
    list_filter = ['payment_method', 'created_at']
    search_fields = ['debt__customer__name']
    ordering = ['-created_at']

@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_sales', 'total_profit', 'total_transactions', 'average_transaction_value']
    list_filter = ['date']
    ordering = ['-date']
    readonly_fields = ['average_transaction_value', 'created_at']
    
    def average_transaction_value(self, obj):
        return obj.average_transaction_value
    average_transaction_value.short_description = 'Avg Transaction Value'
