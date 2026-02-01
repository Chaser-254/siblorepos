from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class ShopProfile(models.Model):
    """Extended profile for shop admins with website information"""
    user_profile = models.OneToOneField('users.UserProfile', on_delete=models.CASCADE, related_name='shop_website')
    business_name = models.CharField(max_length=200)
    business_description = models.TextField(help_text="Describe your business and products")
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=20)
    business_address = models.CharField(max_length=300)
    business_city = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True)
    is_website_active = models.BooleanField(default=True, help_text="Enable/disable your public website")
    website_theme = models.CharField(max_length=20, choices=[
        ('default', 'Default Theme'),
        ('modern', 'Modern Theme'),
        ('classic', 'Classic Theme'),
    ], default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Shop Website Profile"
        verbose_name_plural = "Shop Website Profiles"
    
    def __str__(self):
        return f"{self.business_name} Website"
    
    @property
    def shop_url(self):
        return f"/shop/{self.user_profile.user.username}/"


class ShopProduct(models.Model):
    """Products that shop admins want to display on their website"""
    shop_profile = models.ForeignKey(ShopProfile, on_delete=models.CASCADE, related_name='website_products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                       help_text="Original price for discount display")
    image = models.ImageField(upload_to='shop_products/')
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    is_available = models.BooleanField(default=True)
    category = models.CharField(max_length=100, help_text="Product category for website display")
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Shop Website Product"
        verbose_name_plural = "Shop Website Products"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.shop_profile.business_name}"
    
    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100, 1)
        return 0
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class Cart(models.Model):
    """Shopping cart for customers"""
    cart_id = models.CharField(max_length=100, unique=True)
    shop_profile = models.ForeignKey(ShopProfile, on_delete=models.CASCADE, related_name='carts')
    customer_name = models.CharField(max_length=100, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
    
    def __str__(self):
        return f"Cart {self.cart_id} - {self.shop_profile.business_name}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def is_empty(self):
        return self.items.count() == 0


class CartItem(models.Model):
    """Individual items in a shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ShopProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart.cart_id}"
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """Orders placed through the website"""
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('SIGNED', 'Signed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    shop_profile = models.ForeignKey(ShopProfile, on_delete=models.CASCADE, related_name='orders')
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    delivery_address = models.TextField(blank=True, help_text="Leave empty for pickup")
    notes = models.TextField(blank=True, help_text="Special instructions or notes")
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    customer_signature = models.ImageField(upload_to='signatures/', blank=True, null=True, help_text="Customer signature for delivered orders")
    signed_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when order was signed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - {self.shop_profile.business_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            import uuid
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ShopProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)
