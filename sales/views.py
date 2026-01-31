from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json
from .models import Customer, Sale, SaleItem, Debt, DebtPayment, Revenue
from products.models import Product, Stock, Category, StockMovement
from users.decorators import admin_required, can_view_reports, get_user_profile
import uuid

@login_required
def dashboard(request):
    # Get today's stats
    today = timezone.now().date()
    
    # Get user profile
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
    else:
        profile = None
    
    # Filter sales based on user role
    if profile and profile.can_view_own_sales_only():
        # Cashiers can only see their own sales
        today_sales = Sale.objects.filter(
            created_at__date=today, 
            status='COMPLETED',
            created_by=request.user.username
        )
        recent_sales = Sale.objects.filter(
            status='COMPLETED',
            created_by=request.user.username
        ).order_by('-created_at')[:10]
    else:
        # Admins can see all sales
        today_sales = Sale.objects.filter(created_at__date=today, status='COMPLETED')
        recent_sales = Sale.objects.filter(status='COMPLETED').order_by('-created_at')[:10]
    
    total_sales_today = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_transactions_today = today_sales.count()
    
    # Revenue stats - only admins can see revenue
    if profile and profile.can_view_revenue_debts():
        revenue_today = Revenue.objects.filter(date=today).first()
        if not revenue_today:
            revenue_today = Revenue.objects.create(date=today)
        
        # Debt stats - only admins can see debts
        total_debts = Debt.objects.filter(status__in=['PENDING', 'PARTIAL']).aggregate(total=Sum('balance'))['total'] or 0
        overdue_debts = Debt.objects.filter(status='OVERDUE').aggregate(total=Sum('balance'))['total'] or 0
    else:
        revenue_today = None
        total_debts = 0
        overdue_debts = 0
    
    # Top selling products - only admins can see
    if profile and profile.can_view_all_reports():
        top_products = Product.objects.filter(
            saleitem__sale__created_at__date=today,
            saleitem__sale__status='COMPLETED'
        ).annotate(
            total_sold=Sum('saleitem__quantity'),
            total_revenue=Sum('saleitem__total_price')
        ).order_by('-total_sold')[:5]
        
        # Low stock alerts - only admins can see
        low_stock_products = Stock.objects.filter(
            quantity__lte=F('reorder_level'),
            is_active=True
        ).select_related('product')[:5]
    else:
        top_products = []
        low_stock_products = []
    
    context = {
        'total_sales_today': total_sales_today,
        'total_transactions_today': total_transactions_today,
        'revenue_today': revenue_today,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'recent_sales': recent_sales,
        'total_debts': total_debts,
        'overdue_debts': overdue_debts,
    }
    
    return render(request, 'sales/dashboard.html', context)

@login_required
def pos_terminal(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('stock_records')
    categories = Category.objects.all()
    customers = Customer.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'customers': customers,
    }
    return render(request, 'sales/pos_terminal.html', context)

@login_required
def process_sale(request):
    if request.method == 'POST':
        try:
            data = request.POST
            customer_id = data.get('customer_id')
            payment_method = data.get('payment_method')
            items = data.getlist('items')
            quantities = data.getlist('quantities')
            notes = data.get('notes', '')
            
            # Generate invoice number
            invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Create sale
            customer = None
            if customer_id:
                customer = Customer.objects.get(id=customer_id)
            
            sale = Sale.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                payment_method=payment_method,
                status='COMPLETED',
                subtotal=0,
                total_amount=0,
                notes=notes,
                created_by=request.user.username if request.user.is_authenticated else 'Anonymous'
            )
            
            subtotal = Decimal('0')
            
            # Process each item
            for item_id, quantity in zip(items, quantities):
                product = Product.objects.get(id=item_id)
                quantity = int(quantity)
                
                # Check stock
                stock = product.stock_records.first()
                if stock.quantity < quantity:
                    return JsonResponse({'success': False, 'message': f'Insufficient stock for {product.name}'})
                
                # Create sale item
                unit_price = product.selling_price
                total_price = quantity * unit_price
                
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                
                # Update stock
                stock.quantity -= quantity
                stock.save()
                
                # Create stock movement
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                    reference=f"Sale {invoice_number}",
                    created_by=request.user.username if request.user.is_authenticated else 'Anonymous'
                )
                
                subtotal += total_price
            
            # Update sale totals
            sale.subtotal = subtotal
            sale.total_amount = subtotal
            sale.amount_paid = subtotal if payment_method != 'CREDIT' else 0
            sale.save()
            
            # Create debt if credit payment
            if payment_method == 'CREDIT' and customer:
                Debt.objects.create(
                    customer=customer,
                    sale=sale,
                    amount=subtotal,
                    balance=subtotal,
                    due_date=timezone.now().date() + timezone.timedelta(days=30)
                )
            
            # Update revenue
            revenue, created = Revenue.objects.get_or_create(date=timezone.now().date())
            revenue.total_sales += subtotal
            revenue.total_transactions += 1
            
            if payment_method == 'CASH':
                revenue.cash_sales += subtotal
            elif payment_method == 'CARD':
                revenue.card_sales += subtotal
            elif payment_method == 'MOBILE':
                revenue.mobile_sales += subtotal
            elif payment_method == 'BANK':
                revenue.bank_sales += subtotal
            elif payment_method == 'CREDIT':
                revenue.credit_sales += subtotal
            
            revenue.save()
            
            return JsonResponse({
                'success': True,
                'sale_id': sale.id,
                'invoice_number': invoice_number,
                'total_amount': float(subtotal)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def sales_list(request):
    # Get user profile
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
    else:
        profile = None
    
    # Filter sales based on user role
    if profile and profile.can_view_own_sales_only():
        sales = Sale.objects.filter(
            created_by=request.user.username
        ).select_related('customer').prefetch_related('sale_items').order_by('-created_at')
    else:
        sales = Sale.objects.select_related('customer').prefetch_related('sale_items').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    payment_method = request.GET.get('payment_method')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        sales = sales.filter(status=status)
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    
    # Calculate statistics
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    items_sold = sum(sale.sale_items.aggregate(total=Sum('quantity'))['total'] or 0 for sale in sales)
    average_sale = total_revenue / sales.count() if sales.count() > 0 else 0
    
    context = {
        'sales': sales,
        'status_choices': Sale.STATUS_CHOICES,
        'payment_choices': Sale.PAYMENT_METHODS,
        'total_revenue': total_revenue,
        'items_sold': items_sold,
        'average_sale': average_sale,
    }
    return render(request, 'sales/sales_list.html', context)

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('sale_items__product'), pk=pk)
    return render(request, 'sales/sale_detail.html', {'sale': sale})

@login_required
def sale_receipt(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('sale_items__product'), pk=pk)
    
    # Get business information from the current user's profile or system defaults
    business_info = {
        'name': 'SibLore POS',
        'address': '123 Business Street',
        'city': 'Nairobi',
        'phone': '+254 123 456 789',
        'email': 'info@siblore.com',
    }
    
    # Try to get business info from user profile if available
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        
        # If current user is a cashier, get business info from their shop admin
        if profile.is_cashier and profile.shop_admin:
            admin_profile = profile.shop_admin
            if admin_profile.shop_name:
                business_info['name'] = admin_profile.shop_name
            if admin_profile.shop_address:
                business_info['address'] = admin_profile.shop_address
            if admin_profile.shop_city:
                business_info['city'] = admin_profile.shop_city
            if admin_profile.shop_phone:
                business_info['phone'] = admin_profile.shop_phone
            if admin_profile.shop_email:
                business_info['email'] = admin_profile.shop_email
        else:
            # For shop admins or site admins, use their own business info
            if profile.shop_name:
                business_info['name'] = profile.shop_name
            if profile.shop_address:
                business_info['address'] = profile.shop_address
            if profile.shop_city:
                business_info['city'] = profile.shop_city
            if profile.shop_phone:
                business_info['phone'] = profile.shop_phone
            if profile.shop_email:
                business_info['email'] = profile.shop_email
    
    context = {
        'sale': sale,
        'business': business_info,
    }
    return render(request, 'sales/receipt.html', context)

@login_required
def sale_delete(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('sale_items'), pk=pk)
    
    # Get user profile
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
    else:
        profile = None
    
    # Check if user can delete sales
    if not profile or not profile.can_delete_sales():
        messages.error(request, 'Access denied. Only admins can delete sales.')
        return redirect('sales:sales_list')
    
    # Additional check: cashiers can only delete their own sales (though they shouldn't be able to delete at all)
    if profile and profile.can_view_own_sales_only() and sale.created_by != request.user.username:
        messages.error(request, 'Access denied. You can only manage your own sales.')
        return redirect('sales:sales_list')
    
    if request.method == 'POST':
        confirm_invoice = request.POST.get('confirm_invoice', '')
        if confirm_invoice == sale.invoice_number:
            # Store sale info for message
            invoice_number = sale.invoice_number
            
            # Restore stock quantities
            for item in sale.sale_items.all():
                stock = item.product.stock_records.first()
                if stock:
                    stock.quantity += item.quantity
                    stock.save()
            
            # Delete the sale (this will cascade delete sale items, debt records, etc.)
            sale.delete()
            
            messages.success(request, f'Sale {invoice_number} deleted successfully! Stock has been restored.')
            return redirect('sales:sales_list')
        else:
            messages.error(request, 'Invoice number confirmation does not match. Please type the exact invoice number.')
    
    return render(request, 'sales/sale_delete.html', {'sale': sale})

@login_required
def customers_list(request):
    customers = Customer.objects.annotate(
        total_debt_amount=Sum('debts__balance', filter=Q(debts__status__in=['PENDING', 'PARTIAL']))
    ).order_by('name')
    
    # Calculate active customers count
    active_customers_count = Customer.objects.filter(is_active=True).count()
    
    context = {
        'customers': customers,
        'active_customers_count': active_customers_count,
    }
    return render(request, 'sales/customers_list.html', context)

@login_required
def customer_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        credit_limit = request.POST.get('credit_limit', 0)
        
        customer = Customer.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address,
            credit_limit=credit_limit
        )
        
        messages.success(request, f'Customer "{customer.name}" created successfully!')
        return redirect('sales:customers_list')
    
    return render(request, 'sales/customer_form.html', {'title': 'Add Customer'})

@login_required
def debts_list(request):
    debts = Debt.objects.select_related('customer', 'sale').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    if status:
        debts = debts.filter(status=status)
    
    context = {
        'debts': debts,
        'status_choices': Debt.STATUS_CHOICES,
    }
    return render(request, 'sales/debts_list.html', context)

@login_required
def pay_debt(request, pk):
    debt = get_object_or_404(Debt.objects.select_related('customer'), pk=pk)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes', '')
        
        if amount <= 0:
            messages.error(request, 'Payment amount must be greater than 0!')
        elif amount > debt.balance:
            messages.error(request, 'Payment amount cannot exceed debt balance!')
        else:
            # Create payment
            DebtPayment.objects.create(
                debt=debt,
                amount=amount,
                payment_method=payment_method,
                notes=notes,
                created_by=request.user.username if request.user.is_authenticated else 'Anonymous'
            )
            
            # Update debt
            debt.amount_paid += amount
            debt.save()
            
            messages.success(request, f'Payment of {amount} recorded successfully!')
            return redirect('sales:debts_list')
    
    return render(request, 'sales/pay_debt.html', {'debt': debt})

@can_view_reports
def reports(request):
    # Get date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = timezone.now().date() - timezone.timedelta(days=30)
    if not date_to:
        date_to = timezone.now().date()
    
    # Get revenue data
    revenues = Revenue.objects.filter(date__range=[date_from, date_to]).order_by('date')
    
    # Get sales data
    sales = Sale.objects.filter(
        created_at__date__range=[date_from, date_to],
        status='COMPLETED'
    ).select_related('customer').prefetch_related('sale_items__product')
    
    # Calculate totals
    total_sales = revenues.aggregate(total=Sum('total_sales'))['total'] or 0
    total_profit = revenues.aggregate(total=Sum('total_profit'))['total'] or 0
    total_transactions = revenues.aggregate(total=Sum('total_transactions'))['total'] or 0
    average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Payment method breakdown
    payment_breakdown = {
        'cash': revenues.aggregate(total=Sum('cash_sales'))['total'] or 0,
        'card': revenues.aggregate(total=Sum('card_sales'))['total'] or 0,
        'mobile': revenues.aggregate(total=Sum('mobile_sales'))['total'] or 0,
        'bank': revenues.aggregate(total=Sum('bank_sales'))['total'] or 0,
        'credit': revenues.aggregate(total=Sum('credit_sales'))['total'] or 0,
    }
    
    # Prepare data for revenue chart
    revenue_chart_data = json.dumps([float(revenue.total_sales) for revenue in revenues])
    revenue_chart_labels = json.dumps([revenue.date.strftime('%b %d') for revenue in revenues])
    
    context = {
        'revenues': revenues,
        'sales': sales,
        'total_sales': total_sales,
        'total_profit': total_profit,
        'total_transactions': total_transactions,
        'average_transaction': average_transaction,
        'payment_breakdown': payment_breakdown,
        'date_from': date_from,
        'date_to': date_to,
        'revenue_chart_data': revenue_chart_data,
        'revenue_chart_labels': revenue_chart_labels,
    }
    
    return render(request, 'sales/reports.html', context)

@can_view_reports
def report_print(request):
    # Get date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = timezone.now().date() - timezone.timedelta(days=30)
    if not date_to:
        date_to = timezone.now().date()
    
    # Get revenue data
    revenues = Revenue.objects.filter(date__range=[date_from, date_to]).order_by('date')
    
    # Get sales data
    sales = Sale.objects.filter(
        created_at__date__range=[date_from, date_to],
        status='COMPLETED'
    ).select_related('customer').prefetch_related('sale_items__product')
    
    # Calculate totals
    total_sales = revenues.aggregate(total=Sum('total_sales'))['total'] or 0
    total_profit = revenues.aggregate(total=Sum('total_profit'))['total'] or 0
    total_transactions = revenues.aggregate(total=Sum('total_transactions'))['total'] or 0
    average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Payment method breakdown
    payment_breakdown = {
        'cash': revenues.aggregate(total=Sum('cash_sales'))['total'] or 0,
        'card': revenues.aggregate(total=Sum('card_sales'))['total'] or 0,
        'mobile': revenues.aggregate(total=Sum('mobile_sales'))['total'] or 0,
        'bank': revenues.aggregate(total=Sum('bank_sales'))['total'] or 0,
        'credit': revenues.aggregate(total=Sum('credit_sales'))['total'] or 0,
    }
    
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_profit': total_profit,
        'total_transactions': total_transactions,
        'average_transaction': average_transaction,
        'payment_breakdown': payment_breakdown,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'sales/report_print.html', context)
