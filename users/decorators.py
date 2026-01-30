from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps
from .models import UserProfile

def get_user_profile(user):
    """Get or create user profile"""
    profile, created = UserProfile.objects.get_or_create(user=user)
    return profile

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
