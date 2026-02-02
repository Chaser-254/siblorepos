from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import base64
import io
import json
from PIL import Image
from django.core.files.base import ContentFile
from .models import UserProfile, RegistrationRequest
from .forms import UserCreationForm, UserUpdateForm, CashierCreationForm, CashierUpdateForm, BusinessDetailsForm
from .decorators import get_user_profile

def landing_page(request):
    """Landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('sales:dashboard')
    return render(request, 'landing.html')

def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on user type
        if request.user.is_superuser:
            return redirect('users:site_owner_dashboard')
        elif request.user.profile.is_shop_admin:
            return redirect('users:shop_admin_dashboard')
        elif request.user.profile.is_cashier:
            return redirect('users:cashier_dashboard')
        else:
            return redirect('sales:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Ensure user profile exists
                get_user_profile(user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect based on user type
                if user.is_superuser:
                    return redirect('users:site_owner_dashboard')
                elif user.profile.is_shop_admin:
                    return redirect('users:shop_admin_dashboard')
                elif user.profile.is_cashier:
                    return redirect('users:cashier_dashboard')
                else:
                    return redirect('sales:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

def register_request(request):
    if request.user.is_authenticated:
        return redirect('sales:dashboard')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        desired_role = request.POST.get('desired_role')
        reason = request.POST.get('reason')
        
        # Save the registration request to database
        RegistrationRequest.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            desired_role=desired_role,
            reason=reason
        )
        
        messages.success(request, 
            f'Your account request has been submitted successfully! '
            f'The administrator will contact you soon at {email} or {phone}.'
        )
        return redirect('users:login')
    
    return render(request, 'users/register_request.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('users:login')

@login_required
def registration_requests(request):
    """View for admins to see and manage registration requests"""
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. Only site administrators can view registration requests.')
        return redirect('sales:dashboard')
    
    requests = RegistrationRequest.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Get pending requests count for navigation
    pending_count = RegistrationRequest.objects.filter(status='PENDING').count()
    
    context = {
        'requests': requests,
        'status_choices': RegistrationRequest.STATUS_CHOICES,
        'current_status': status_filter,
        'pending_requests_count': pending_count,
    }
    return render(request, 'users/registration_requests.html', context)

@login_required
def update_request_status(request, pk):
    """Update the status of a registration request"""
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. Only site administrators can manage registration requests.')
        return redirect('sales:dashboard')
    
    registration_request = get_object_or_404(RegistrationRequest, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(RegistrationRequest.STATUS_CHOICES).keys():
            registration_request.status = new_status
            registration_request.notes = notes
            registration_request.save()
            
            messages.success(request, f'Request for {registration_request.full_name} has been {new_status.lower()}.')
            
            # If approved, you could create the user account here
            if new_status == 'APPROVED':
                # TODO: Create user account and send credentials
                messages.info(request, f'You should now create an account for {registration_request.full_name} and send them the login details.')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('users:registration_requests')

@login_required
def delete_request(request, pk):
    """Delete a registration request"""
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. Only site administrators can delete registration requests.')
        return redirect('sales:dashboard')
    
    registration_request = get_object_or_404(RegistrationRequest, pk=pk)
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        if str(registration_request.pk) == request_id:
            registration_request.delete()
            messages.success(request, f'Registration request for {registration_request.full_name} has been deleted.')
        else:
            messages.error(request, 'Invalid request.')
    
    return redirect('users:registration_requests')

@login_required
def pos_admin_dashboard(request):
    """POS Admin Dashboard - separate from Django admin"""
    profile = get_user_profile(request.user)
    if not profile.is_admin:
        messages.error(request, 'Access denied. Only POS administrators can access this dashboard.')
        return redirect('sales:dashboard')
    
    # Get statistics for POS admin
    from sales.models import Sale, Customer, Debt
    from products.models import Product, Stock
    from users.models import UserProfile, RegistrationRequest
    
    # Sales statistics
    today_sales = Sale.objects.filter(created_at__date=timezone.now().date()).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Customer statistics
    total_customers = Customer.objects.count()
    total_debts = Debt.objects.aggregate(total=Sum('amount'))['total'] or 0
    paid_debts = Debt.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    outstanding_debts = total_debts - paid_debts
    
    # Product statistics
    total_products = Product.objects.count()
    low_stock_products = Stock.objects.filter(quantity__lte=F('reorder_level')).count()
    
    # User statistics
    total_users = UserProfile.objects.filter(is_active=True).count()
    pending_requests = RegistrationRequest.objects.filter(status='PENDING').count()
    
    context = {
        'today_sales_total': today_sales['total'] or 0,
        'today_sales_count': today_sales['count'] or 0,
        'total_customers': total_customers,
        'total_debts': total_debts,
        'outstanding_debts': outstanding_debts,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_users': total_users,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'users/pos_admin_dashboard.html', context)

@login_required
def shop_admin_dashboard(request):
    """Shop Admin Dashboard - for shop administrators"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can access this dashboard.')
        return redirect('sales:dashboard')
    
    # Get shop-specific statistics
    from sales.models import Sale, Customer, Debt
    from products.models import Product, Stock
    from users.models import UserProfile, RegistrationRequest
    from invoicing.models import Invoice
    
    # Invoice statistics - filtered by shop
    invoice_stats = Invoice.objects.filter(shop_admin=profile).aggregate(
        total_invoices=Count('id'),
        total_amount=Sum('total_amount'),
        paid_amount=Sum('amount_paid')
    )
    # Calculate pending amount separately
    invoice_stats['pending_amount'] = (invoice_stats['total_amount'] or 0) - (invoice_stats['paid_amount'] or 0)
    
    # Recent invoices - filtered by shop
    recent_invoices = Invoice.objects.filter(
        shop_admin=profile
    ).select_related('customer').order_by('-created_at')[:5]
    
    # Sales statistics - filtered by shop
    today_sales = Sale.objects.filter(
        created_at__date=timezone.now().date(),
        shop_admin=profile
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Customer statistics - filtered by shop
    total_customers = Customer.objects.filter(
        sale__shop_admin=profile
    ).distinct().count()
    total_debts = Debt.objects.filter(
        sale__shop_admin=profile
    ).aggregate(total=Sum('amount'))['total'] or 0
    paid_debts = Debt.objects.filter(
        sale__shop_admin=profile,
        status='PAID'
    ).aggregate(total=Sum('amount'))['total'] or 0
    outstanding_debts = total_debts - paid_debts
    
    # Product statistics - filtered by shop
    total_products = Product.objects.filter(shop_admin=profile).count()
    low_stock_products = Stock.objects.filter(
        product__shop_admin=profile,
        quantity__lte=F('reorder_level')
    ).count()
    
    # Staff statistics - filtered by shop
    cashiers = UserProfile.objects.filter(
        shop_admin=profile,
        role='CASHIER',
        is_active=True
    ).count()
    pending_requests = RegistrationRequest.objects.filter(status='PENDING').count()
    
    # Recent activity - filtered by shop
    recent_sales = Sale.objects.filter(
        shop_admin=profile
    ).select_related('customer').order_by('-created_at')[:5]
    
    # Website statistics
    try:
        from shop_website.models import ShopProfile, ShopProduct, Order
        shop_profile = profile.shop_website
        website_products = ShopProduct.objects.filter(shop_profile=shop_profile).count()
        website_orders = Order.objects.filter(shop_profile=shop_profile).count()
        recent_website_orders = Order.objects.filter(shop_profile=shop_profile).order_by('-created_at')[:5]
        
        # Calculate website revenue
        website_revenue = Order.objects.filter(
            shop_profile=shop_profile,
            order_status__in=['CONFIRMED', 'PREPARING', 'READY', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
    except:
        shop_profile = None
        website_products = 0
        website_orders = 0
        website_revenue = 0
        recent_website_orders = []
    
    context = {
        'today_sales_total': today_sales['total'] or 0,
        'today_sales_count': today_sales['count'] or 0,
        'total_customers': total_customers,
        'total_debts': total_debts,
        'outstanding_debts': outstanding_debts,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'cashiers': cashiers,
        'pending_requests': pending_requests,
        'recent_sales': recent_sales,
        # Invoice data
        'invoice_stats': invoice_stats,
        'recent_invoices': recent_invoices,
        # Website data
        'shop_profile': shop_profile,
        'website_products': website_products,
        'website_orders': website_orders,
        'website_revenue': website_revenue,
        'recent_website_orders': recent_website_orders,
        'currency': 'KES',
        'currency_symbol': 'KSh',
    }
    
    return render(request, 'users/shop_admin_dashboard.html', context)

@login_required
def site_owner_dashboard(request):
    """Site Owner Dashboard - for Django superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only site owners can access this dashboard.')
        return redirect('sales:dashboard')
    
    # Get system-wide statistics for site owner
    from sales.models import Sale, Customer, Debt
    from products.models import Product, Stock, Category
    from users.models import UserProfile, RegistrationRequest
    from django.contrib.auth.models import User
    
    # System statistics
    total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_transactions = Sale.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_users = User.objects.count()
    active_users = UserProfile.objects.filter(is_active=True).count()
    pending_requests = RegistrationRequest.objects.filter(status='PENDING').count()
    
    # Recent activity
    recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:5]
    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:5]
    recent_requests = RegistrationRequest.objects.order_by('-created_at')[:5]
    
    # System health
    low_stock_products = Stock.objects.filter(quantity__lte=F('reorder_level')).count()
    total_debts = Debt.objects.aggregate(total=Sum('amount'))['total'] or 0
    paid_debts = Debt.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
    outstanding_debts = total_debts - paid_debts
    
    context = {
        # System Overview
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_users': total_users,
        'active_users': active_users,
        'pending_requests': pending_requests,
        
        # Financial Overview
        'total_debts': total_debts,
        'outstanding_debts': outstanding_debts,
        'paid_debts': paid_debts,
        
        # System Health
        'low_stock_products': low_stock_products,
        
        # Recent Activity
        'recent_sales': recent_sales,
        'recent_users': recent_users,
        'recent_requests': recent_requests,
        
        # Currency
        'currency': 'KES',
        'currency_symbol': 'KSh',
    }
    
    return render(request, 'users/site_owner_dashboard.html', context)

@login_required
def cashier_list(request):
    """View for shop admins to manage cashiers"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access cashier management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not (profile.is_site_admin or profile.is_shop_admin):
        messages.error(request, 'Access denied. Cashier management requires admin privileges.')
        return redirect('sales:dashboard')
    
    # Only show cashiers for this shop admin (or all for site admin)
    if profile.is_site_admin:
        cashiers = User.objects.filter(profile__role='CASHIER').select_related('profile').order_by('username')
    else:
        cashiers = User.objects.filter(profile__role='CASHIER', profile__shop_admin=profile).select_related('profile').order_by('username')
    
    return render(request, 'users/cashier_list.html', {'cashiers': cashiers})

@login_required
def cashier_create(request):
    """Create a new cashier user"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access cashier management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not (profile.is_site_admin or profile.is_shop_admin):
        messages.error(request, 'Access denied. Cashier management requires admin privileges.')
        return redirect('sales:dashboard')
    
    if request.method == 'POST':
        form = CashierCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create cashier profile
            UserProfile.objects.create(
                user=user,
                role='CASHIER',  # Force role to be CASHIER
                phone=form.cleaned_data['phone'],
                shop_admin=profile if profile.is_shop_admin else None  # Assign to shop admin
            )
            messages.success(request, f'Cashier "{user.username}" created successfully!')
            return redirect('users:cashier_list')
    else:
        form = CashierCreationForm()
    
    return render(request, 'users/cashier_form.html', {'form': form, 'title': 'Create Cashier'})

@login_required
def cashier_update(request, pk):
    """Update cashier profile"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access cashier management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not (profile.is_site_admin or profile.is_shop_admin):
        messages.error(request, 'Access denied. Cashier management requires admin privileges.')
        return redirect('sales:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if user.profile.role != 'CASHIER':
        messages.error(request, 'This user is not a cashier.')
        return redirect('users:cashier_list')
    
    # Check if shop admin can only manage their own cashiers
    if profile.is_shop_admin and user.profile.shop_admin != profile:
        messages.error(request, 'Access denied. You can only manage your own cashiers.')
        return redirect('users:cashier_list')
    
    if request.method == 'POST':
        form = CashierUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Update user profile
            user_profile = user.profile
            user_profile.phone = form.cleaned_data['phone']
            user_profile.is_active = form.cleaned_data['is_active']
            user_profile.save()
            messages.success(request, f'Cashier "{user.username}" updated successfully!')
            return redirect('users:cashier_list')
    else:
        form = CashierUpdateForm(instance=user)
    
    return render(request, 'users/cashier_form.html', {'form': form, 'title': 'Update Cashier', 'user': user})

@login_required
def cashier_toggle_active(request, pk):
    """Toggle cashier active status"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access cashier management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not (profile.is_site_admin or profile.is_shop_admin):
        messages.error(request, 'Access denied. Cashier management requires admin privileges.')
        return redirect('sales:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if user.profile.role != 'CASHIER':
        messages.error(request, 'This user is not a cashier.')
        return redirect('users:cashier_list')
    
    # Check if shop admin can only manage their own cashiers
    if profile.is_shop_admin and user.profile.shop_admin != profile:
        messages.error(request, 'Access denied. You can only manage your own cashiers.')
        return redirect('users:cashier_list')
    
    user_profile = user.profile
    user_profile.is_active = not user_profile.is_active
    user_profile.save()
    
    status = "activated" if user_profile.is_active else "deactivated"
    messages.success(request, f'Cashier "{user.username}" {status} successfully!')
    return redirect('users:cashier_list')

def user_list(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access user management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. User management requires site admin privileges.')
        return redirect('sales:dashboard')
    
    users = User.objects.all().select_related('profile').order_by('username')
    return render(request, 'users/user_list.html', {'users': users})

@login_required
def business_details(request):
    """View for shop admins to update their business details"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access business settings.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Business settings require shop admin privileges.')
        return redirect('sales:dashboard')
    
    if request.method == 'POST':
        form = BusinessDetailsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business details updated successfully!')
            return redirect('users:business_details')
    else:
        form = BusinessDetailsForm(instance=profile)
    
    return render(request, 'users/business_details.html', {'form': form, 'profile': profile})

def user_create(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access user management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. User management requires site admin privileges.')
        return redirect('sales:dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(
                user=user,
                role=form.cleaned_data['role'],
                phone=form.cleaned_data['phone'],
                shop_name=form.cleaned_data.get('shop_name') if form.cleaned_data['role'] == 'SHOP_ADMIN' else None
            )
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('users:user_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Create User'})

def user_update(request, pk):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access user management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. User management requires site admin privileges.')
        return redirect('sales:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Update user profile
            user_profile = user.profile
            user_profile.role = form.cleaned_data['role']
            user_profile.phone = form.cleaned_data['phone']
            user_profile.is_active = form.cleaned_data['is_active']
            user_profile.shop_name = form.cleaned_data.get('shop_name') if form.cleaned_data['role'] == 'SHOP_ADMIN' else None
            user_profile.save()
            
            messages.success(request, f'User "{user.username}" updated successfully!')
            return redirect('users:user_list')
    else:
        form = UserUpdateForm(instance=user, initial={
            'role': user.profile.role,
            'phone': user.profile.phone,
            'is_active': user.profile.is_active,
            'shop_name': user.profile.shop_name,
        })
    
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Update User', 'user': user})

@login_required
def cashier_dashboard(request):
    """Cashier Dashboard - for cashiers to view website and process orders"""
    profile = get_user_profile(request.user)
    if not profile.is_cashier:
        messages.error(request, 'Access denied. This dashboard is for cashiers only.')
        return redirect('sales:dashboard')
    
    # Get shop admin's website and orders
    shop_admin = profile.shop_admin
    if not shop_admin:
        messages.error(request, 'Your account is not assigned to any shop administrator.')
        return redirect('sales:dashboard')
    
    # Get website information and orders
    try:
        from shop_website.models import ShopProfile, Order
        shop_profile = shop_admin.shop_website
        website_orders = Order.objects.filter(shop_profile=shop_profile).order_by('-created_at')
        pending_orders = website_orders.filter(order_status='PENDING')
        confirmed_orders = website_orders.filter(order_status='CONFIRMED')
        preparing_orders = website_orders.filter(order_status='PREPARING')
        ready_orders = website_orders.filter(order_status='READY')
        completed_orders = website_orders.filter(order_status='COMPLETED')
        
        # Calculate statistics
        total_orders = website_orders.count()
        pending_count = pending_orders.count()
        confirmed_count = confirmed_orders.count()
        preparing_count = preparing_orders.count()
        ready_count = ready_orders.count()
        completed_count = completed_orders.count()
        
        # Recent orders for display
        recent_orders = website_orders[:10]
        
        # Website URL
        website_url = shop_profile.shop_url
        
    except:
        shop_profile = None
        website_orders = []
        pending_orders = []
        confirmed_orders = []
        preparing_orders = []
        ready_orders = []
        completed_orders = []
        total_orders = 0
        pending_count = 0
        confirmed_count = 0
        preparing_count = 0
        ready_count = 0
        completed_count = 0
        recent_orders = []
        website_url = '#'
    
    context = {
        'shop_profile': shop_profile,
        'shop_admin': shop_admin,
        'website_url': website_url,
        'total_orders': total_orders,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'preparing_count': preparing_count,
        'ready_count': ready_count,
        'completed_count': completed_count,
        'recent_orders': recent_orders,
        'currency': 'KES',
        'currency_symbol': 'KSh',
    }
    
    return render(request, 'users/cashier_dashboard.html', context)

@login_required
def cashier_orders(request):
    """View for cashiers to see and process website orders"""
    profile = get_user_profile(request.user)
    if not profile.is_cashier:
        messages.error(request, 'Access denied. This page is for cashiers only.')
        return redirect('sales:dashboard')
    
    # Get shop admin's website and orders
    shop_admin = profile.shop_admin
    if not shop_admin:
        messages.error(request, 'Your account is not assigned to any shop administrator.')
        return redirect('sales:dashboard')
    
    # Get status filter before the try block
    status_filter = request.GET.get('status')
    
    try:
        from shop_website.models import ShopProfile, Order
        shop_profile = shop_admin.shop_website
        orders = Order.objects.filter(shop_profile=shop_profile).order_by('-created_at')
        
        # Filter by status if provided
        if status_filter:
            orders = orders.filter(order_status=status_filter)
        
    except:
        orders = []
    
    context = {
        'orders': orders,
        'status_choices': [
            ('PENDING', 'Pending'),
            ('CONFIRMED', 'Confirmed'),
            ('PROCESSING', 'Processing'),
            ('IN_TRANSIT', 'In Transit'),
            ('DELIVERED', 'Delivered'),
            ('SIGNED', 'Signed'),
            ('CANCELLED', 'Cancelled'),
        ],
        'current_status': status_filter,
    }
    
    return render(request, 'users/cashier_orders.html', context)

@login_required
def cashier_update_order_status(request, pk):
    """Update order status for cashiers"""
    profile = get_user_profile(request.user)
    if not profile.is_cashier:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Access denied'})
        messages.error(request, 'Access denied. This action is for cashiers only.')
        return redirect('sales:dashboard')
    
    # Get shop admin's website
    shop_admin = profile.shop_admin
    if not shop_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Your account is not assigned to any shop administrator'})
        messages.error(request, 'Your account is not assigned to any shop administrator.')
        return redirect('sales:dashboard')
    
    try:
        from shop_website.models import ShopProfile, Order
        shop_profile = shop_admin.shop_website
        order = get_object_or_404(Order, pk=pk, shop_profile=shop_profile)
        
        if request.method == 'POST':
            new_status = request.POST.get('status')
            valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
            
            if new_status in valid_statuses:
                old_status = order.order_status
                order.order_status = new_status
                order.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Order {order.order_number} status updated from {old_status} to {new_status}.',
                        'old_status': old_status,
                        'new_status': new_status
                    })
                
                messages.success(request, 
                    f'Order {order.order_number} status updated from {old_status} to {new_status}.')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid status selected'})
                messages.error(request, 'Invalid status selected.')
        
        return redirect('users:cashier_orders')
        
    except (ShopProfile.DoesNotExist, Order.DoesNotExist) as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Order not found or access denied'})
        messages.error(request, 'Order not found or access denied.')
        return redirect('users:cashier_orders')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('users:cashier_orders')

@login_required
def cashier_order_detail(request, pk):
    """View order details for cashiers"""
    profile = get_user_profile(request.user)
    if not profile.is_cashier:
        messages.error(request, 'Access denied. This page is for cashiers only.')
        return redirect('sales:dashboard')
    
    # Get shop admin's website
    shop_admin = profile.shop_admin
    if not shop_admin:
        messages.error(request, 'Your account is not assigned to any shop administrator.')
        return redirect('sales:dashboard')
    
    try:
        from shop_website.models import ShopProfile, Order
        shop_profile = shop_admin.shop_website
        if not shop_profile:
            messages.error(request, 'Shop website not configured. Please contact your shop administrator.')
            return redirect('users:cashier_orders')
            
        order = get_object_or_404(Order, pk=pk, shop_profile=shop_profile)
        
        context = {
            'order': order,
            'status_choices': Order.ORDER_STATUS_CHOICES,
        }
        
        return render(request, 'users/cashier_order_detail.html', context)
        
    except (ShopProfile.DoesNotExist, Order.DoesNotExist) as e:
        messages.error(request, 'Order not found or access denied.')
        return redirect('users:cashier_orders')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('users:cashier_orders')

def user_toggle_active(request, pk):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access user management.')
        return redirect('sales:dashboard')
    
    profile = get_user_profile(request.user)
    if not profile.is_site_admin:
        messages.error(request, 'Access denied. User management requires site admin privileges.')
        return redirect('sales:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    user_profile = user.profile
    user_profile.is_active = not user_profile.is_active
    user_profile.save()
    
    status = "activated" if user_profile.is_active else "deactivated"
    messages.success(request, f'User "{user.username}" {status} successfully!')
    return redirect('users:user_list')


@csrf_exempt
@require_POST
@login_required
def cashier_save_signature(request):
    """Save customer signature for an order (cashier version)"""
    try:
        order_id = request.POST.get('order_id')
        signature_data = request.POST.get('signature')
        
        if not order_id or not signature_data:
            return JsonResponse({'success': False, 'error': 'Missing required data'})
        
        # Get user profile and verify cashier
        profile = get_user_profile(request.user)
        if not profile.is_cashier:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        # Get shop admin's website
        shop_admin = profile.shop_admin
        if not shop_admin:
            return JsonResponse({'success': False, 'error': 'Your account is not assigned to any shop administrator'})
        
        # Get order
        from shop_website.models import Order
        shop_profile = shop_admin.shop_website
        if not shop_profile:
            return JsonResponse({'success': False, 'error': 'Shop website not configured'})
            
        order = get_object_or_404(Order, id=order_id, shop_profile=shop_profile)
        
        # Check if order is in correct status for signing
        if order.order_status not in ['DELIVERED', 'SIGNED']:
            return JsonResponse({'success': False, 'error': 'Order must be delivered before signing'})
        
        # Check if signature already exists
        if order.customer_signature:
            return JsonResponse({'success': False, 'error': 'Signature already exists for this order'})
        
        # Process base64 signature data
        format, imgstr = signature_data.split(';base64,')
        ext = format.split('/')[-1]
        
        # Convert base64 to image
        img_data = base64.b64decode(imgstr)
        image = Image.open(io.BytesIO(img_data))
        
        # Save to file
        image_io = io.BytesIO()
        image.save(image_io, format='PNG')
        image_io.seek(0)
        
        # Create filename
        filename = f'signature_order_{order.order_number}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.png'
        
        # Save signature
        order.customer_signature.save(filename, ContentFile(image_io.read()), save=True)
        order.signed_at = timezone.now()
        order.order_status = 'SIGNED'
        order.save()
        
        return JsonResponse({'success': True, 'message': 'Signature saved successfully'})
        
    except (ValueError, IndexError) as e:
        return JsonResponse({'success': False, 'error': 'Invalid signature data format'})
    except (IOError, OSError) as e:
        return JsonResponse({'success': False, 'error': 'Failed to process signature image'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})
