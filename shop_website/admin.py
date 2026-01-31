from django.contrib import admin
from .models import ShopProfile, ShopProduct, Cart, CartItem, Order, OrderItem


@admin.register(ShopProfile)
class ShopProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user_profile', 'is_website_active', 'website_theme', 'created_at']
    list_filter = ['is_website_active', 'website_theme', 'created_at']
    search_fields = ['business_name', 'user_profile__user__username', 'business_email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user_profile', 'business_name', 'business_description')
        }),
        ('Contact Information', {
            'fields': ('business_email', 'business_phone', 'business_address', 'business_city')
        }),
        ('Website Settings', {
            'fields': ('logo', 'is_website_active', 'website_theme')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ShopProduct)
class ShopProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop_profile', 'price', 'stock_quantity', 'is_featured', 'is_available', 'created_at']
    list_filter = ['is_featured', 'is_available', 'category', 'created_at']
    search_fields = ['name', 'description', 'shop_profile__business_name', 'category']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('shop_profile', 'name', 'description', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'is_available')
        }),
        ('Display', {
            'fields': ('image', 'is_featured', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Shop admins can only see their own products
        try:
            shop_profile = request.user.profile.shop_website
            return qs.filter(shop_profile=shop_profile)
        except ShopProfile.DoesNotExist:
            return qs.none()


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'shop_profile', 'customer_name', 'total_items', 'total_price', 'created_at']
    list_filter = ['created_at', 'shop_profile']
    search_fields = ['cart_id', 'customer_name', 'customer_email', 'shop_profile__business_name']
    readonly_fields = ['cart_id', 'created_at', 'updated_at']
    inlines = [CartItemInline]
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'
    
    def total_price(self, obj):
        return f"${obj.total_price}"
    total_price.short_description = 'Total Price'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'shop_profile', 'customer_name', 'total_amount', 'order_status', 'payment_status', 'created_at']
    list_filter = ['order_status', 'payment_status', 'created_at', 'shop_profile']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'shop_profile__business_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'shop_profile', 'created_at')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'notes')
        }),
        ('Order Details', {
            'fields': ('subtotal', 'delivery_fee', 'total_amount')
        }),
        ('Status', {
            'fields': ('order_status', 'payment_status')
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Shop admins can only see their own orders
        try:
            shop_profile = request.user.profile.shop_website
            return qs.filter(shop_profile=shop_profile)
        except ShopProfile.DoesNotExist:
            return qs.none()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
    list_filter = ['order__created_at', 'product__shop_profile']
    search_fields = ['order__order_number', 'product__name', 'product__shop_profile__business_name']
    readonly_fields = ['subtotal']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Shop admins can only see their own order items
        try:
            shop_profile = request.user.profile.shop_website
            return qs.filter(product__shop_profile=shop_profile)
        except ShopProfile.DoesNotExist:
            return qs.none()
