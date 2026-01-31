from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, Count, F
from django.utils import timezone
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
    
    # Sales statistics
    today_sales = Sale.objects.filter(created_at__date=timezone.now().date()).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Customer statistics
    total_customers = Customer.objects.count()
    total_debts = Debt.objects.aggregate(total=Sum('amount'))['total'] or 0
    paid_debts = Debt.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
    outstanding_debts = total_debts - paid_debts
    
    # Product statistics
    total_products = Product.objects.count()
    low_stock_products = Stock.objects.filter(quantity__lte=F('reorder_level')).count()
    
    # Staff statistics
    cashiers = UserProfile.objects.filter(role='CASHIER', is_active=True).count()
    pending_requests = RegistrationRequest.objects.filter(status='PENDING').count()
    
    # Recent activity
    recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:5]
    
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
