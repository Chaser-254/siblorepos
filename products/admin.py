from django.contrib import admin
from .models import Category, Product, Stock, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'selling_price', 'cost_price', 'current_stock', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku', 'barcode']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def current_stock(self, obj):
        return obj.current_stock
    current_stock.short_description = 'Current Stock'

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'reorder_level', 'stock_value', 'last_updated']
    search_fields = ['product__name']
    readonly_fields = ['stock_value', 'last_updated']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'reference', 'created_by', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'reference']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
