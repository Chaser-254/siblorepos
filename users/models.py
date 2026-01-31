from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('SITE_ADMIN', 'Site Administrator'),
        ('SHOP_ADMIN', 'Shop Administrator'),
        ('CASHIER', 'Cashier'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CASHIER')
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    shop_name = models.CharField(max_length=100, blank=True, null=True, help_text="Business/Shop name for Shop Admins")
    shop_address = models.CharField(max_length=200, blank=True, null=True, help_text="Business address")
    shop_city = models.CharField(max_length=100, blank=True, null=True, help_text="Business city")
    shop_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Business phone")
    shop_email = models.EmailField(blank=True, null=True, help_text="Business email")
    shop_admin = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                   limit_choices_to={'role': 'SHOP_ADMIN'}, 
                                   related_name='cashiers',
                                   help_text="Shop Admin this cashier belongs to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        """Check if user is any type of admin (site admin or shop admin)"""
        return self.is_site_admin or self.is_shop_admin
    
    @property
    def is_site_admin(self):
        return self.user.is_superuser
    
    @property
    def is_shop_admin(self):
        return self.role == 'SHOP_ADMIN'
    
    @property
    def is_cashier(self):
        return self.role == 'CASHIER'
    
    def has_full_access(self):
        return self.is_site_admin
    
    def can_manage_products(self):
        return self.is_shop_admin
    
    def can_manage_suppliers(self):
        return self.is_shop_admin
    
    def can_view_all_reports(self):
        return self.is_shop_admin
    
    def can_view_revenue_debts(self):
        return self.is_shop_admin
    
    def can_manage_users(self):
        return self.is_site_admin
    
    def can_manage_cashiers(self):
        return self.is_shop_admin
    
    def can_access_pos(self):
        return True  # All roles can access POS
    
    def can_create_sales(self):
        return True  # All roles can create sales
    
    def can_view_own_sales_only(self):
        return self.is_cashier
    
    def can_delete_sales(self):
        return self.is_shop_admin
    
    def can_view_site_dashboard(self):
        return self.is_site_admin
    
    def can_view_shop_dashboard(self):
        return self.is_shop_admin


class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    ROLE_CHOICES = [
        ('CASHIER', 'Cashier'),
        ('SHOP_ADMIN', 'Shop Administrator'),
        ('SITE_ADMIN', 'Site Administrator'),
    ]
    
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    desired_role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, help_text="Admin notes about this request")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.get_desired_role_display()} ({self.get_status_display()})"
