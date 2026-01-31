from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps
from .models import UserProfile

def get_user_profile(user):
    """Get or create user profile"""
    profile, created = UserProfile.objects.get_or_create(user=user)
    return profile

def get_shop_admin_for_user(user):
    """Get the shop admin for the current user (for cashiers, returns their shop admin; for shop admins, returns themselves)"""
    profile = get_user_profile(user)
    if profile.is_cashier and profile.shop_admin:
        return profile.shop_admin
    elif profile.is_shop_admin:
        return profile
    return None

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_manage_products(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.can_manage_products():
            messages.error(request, 'Access denied. Product management requires admin privileges.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_manage_suppliers(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.can_manage_suppliers():
            messages.error(request, 'Access denied. Supplier management requires admin privileges.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_view_reports(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.can_view_all_reports():
            messages.error(request, 'Access denied. Report viewing requires admin privileges.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_manage_users(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.can_manage_users():
            messages.error(request, 'Access denied. User management requires admin privileges.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def cashier_required(view_func):
    """Decorator to restrict access to cashiers only"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.is_cashier:
            messages.error(request, 'Access denied. This page is for cashiers only.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def shop_admin_required(view_func):
    """Decorator to restrict access to shop admins only"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        if not profile.is_shop_admin:
            messages.error(request, 'Access denied. This page is for shop administrators only.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def site_admin_required(view_func):
    """Decorator to restrict access to site admins only"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Access denied. This page is for site administrators only.')
            return redirect('sales:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def restrict_cashier_access(view_func):
    """Decorator to prevent cashiers from accessing certain pages"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        profile = get_user_profile(request.user)
        if profile.is_cashier:
            messages.error(request, 'Access denied. Cashiers cannot access this page.')
            return redirect('users:cashier_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
