from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Category, Product, Stock, StockMovement
from .forms import ProductForm, CategoryForm, StockForm, StockAdjustmentForm
from users.decorators import can_manage_products

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    
    products = Product.objects.select_related('category').prefetch_related('stock_records')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) | 
            Q(barcode__icontains=query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    categories = Category.objects.all()
    
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
    }
    return render(request, 'products/product_list.html', context)

@can_manage_products
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            Stock.objects.create(product=product, quantity=0)
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('products:product_list')
    else:
        form = ProductForm()
    
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Add Product'})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category').prefetch_related('stock_records', 'stock_movements'), pk=pk)
    stock = product.stock_records.first()
    movements = product.stock_movements.all()[:10]
    
    # Calculate total stock value and profit per unit
    total_stock_value = 0
    profit_per_unit = 0
    if stock:
        total_stock_value = stock.quantity * product.selling_price
        profit_per_unit = product.selling_price - product.cost_price
    
    context = {
        'product': product,
        'stock': stock,
        'movements': movements,
        'total_stock_value': total_stock_value,
        'profit_per_unit': profit_per_unit,
    }
    return render(request, 'products/product_detail.html', context)

@can_manage_products
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('products:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'products/product_form.html', {'form': form, 'product': product, 'title': 'Edit Product'})

@can_manage_products
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        confirm_name = request.POST.get('confirm_name', '')
        if confirm_name == product.name:
            product_name = product.name
            product.delete()
            messages.success(request, f'Product "{product_name}" deleted successfully!')
            return redirect('products:product_list')
        else:
            messages.error(request, 'Product name confirmation does not match. Please type the exact product name.')
    
    return render(request, 'products/product_delete.html', {'product': product})

@login_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('product'))
    return render(request, 'products/category_list.html', {'categories': categories})

@login_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = Product.objects.filter(category=category).select_related('category').prefetch_related('stock_records')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) | 
            Q(barcode__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Filter by stock status
    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = [p for p in products if p.current_stock <= 10]
    elif stock_filter == 'out':
        products = [p for p in products if p.current_stock == 0]
    
    # Calculate statistics
    total_products = products.count()
    total_value = sum(p.selling_price * p.current_stock for p in products)
    low_stock_count = sum(1 for p in products if p.current_stock <= 10)
    out_of_stock_count = sum(1 for p in products if p.current_stock == 0)
    
    # Add calculated value to each product for template
    for product in products:
        product.total_value = product.selling_price * product.current_stock
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'query': query,
        'stock_filter': stock_filter,
        'total_products': total_products,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'products/category_detail.html', context)

@can_manage_products
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('products:category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'products/category_form.html', {'form': form, 'title': 'Add Category'})

@can_manage_products
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('products:category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'products/category_form.html', {'form': form, 'category': category, 'title': 'Edit Category'})

@can_manage_products
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        return redirect('products:category_list')
    
    return render(request, 'products/category_delete.html', {'category': category})

@login_required
def stock_list(request):
    stocks = Stock.objects.select_related('product', 'product__category').filter(is_active=True).order_by('product__name')
    
    # Filter by low stock
    low_stock = request.GET.get('low_stock')
    if low_stock:
        stocks = stocks.filter(quantity__lte=F('reorder_level'))
    
    paginator = Paginator(stocks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate low stock count
    low_stock_count = Stock.objects.filter(is_active=True, quantity__lte=F('reorder_level')).count()
    
    context = {
        'page_obj': page_obj,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
    }
    return render(request, 'products/stock_list.html', context)

@can_manage_products
def stock_adjust(request, pk):
    stock = get_object_or_404(Stock.objects.select_related('product'), pk=pk)
    
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            if adjustment_type == 'IN':
                stock.quantity += quantity
                movement_type = 'IN'
            elif adjustment_type == 'OUT':
                if stock.quantity >= quantity:
                    stock.quantity -= quantity
                    movement_type = 'OUT'
                else:
                    messages.error(request, 'Insufficient stock for this adjustment!')
                    return render(request, 'products/stock_adjust.html', {'form': form, 'stock': stock})
            else:  # ADJUST
                stock.quantity = quantity
                movement_type = 'ADJUST'
            
            stock.save()
            
            # Create stock movement record
            StockMovement.objects.create(
                product=stock.product,
                movement_type=movement_type,
                quantity=quantity,
                notes=notes,
                created_by=request.user.username if request.user.is_authenticated else 'Anonymous'
            )
            
            messages.success(request, f'Stock adjusted successfully!')
            return redirect('products:stock_list')
    else:
        form = StockAdjustmentForm(initial={'quantity': stock.quantity})
    
    return render(request, 'products/stock_adjust.html', {'form': form, 'stock': stock})

@login_required
def stock_movements(request):
    movements = StockMovement.objects.select_related('product').order_by('-created_at')
    
    # Filter by product
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
    
    # Filter by movement type
    movement_type = request.GET.get('movement_type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    # Calculate statistics
    stock_in_count = movements.filter(movement_type='IN').count()
    stock_out_count = movements.filter(movement_type='OUT').count()
    adjustment_count = movements.filter(movement_type='ADJUST').count()
    
    paginator = Paginator(movements, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    products = Product.objects.all()
    
    context = {
        'page_obj': page_obj,
        'products': products,
        'selected_product': product_id,
        'selected_type': movement_type,
        'movement_types': StockMovement.MOVEMENT_TYPES,
        'stock_in_count': stock_in_count,
        'stock_out_count': stock_out_count,
        'adjustment_count': adjustment_count,
    }
    return render(request, 'products/stock_movements.html', context)
