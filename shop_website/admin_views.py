from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.validators import MinValueValidator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
import base64
import io
import json
from PIL import Image
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import ShopProfile, ShopProduct, Order
from users.decorators import get_user_profile


@login_required
def setup_website(request):
    """Setup website for shop admin"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can setup websites.')
        return redirect('users:shop_admin_dashboard')
    
    # Check if website already exists
    try:
        shop_profile = profile.shop_website
        return redirect('shop_website:edit_website')
    except ShopProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        # Create shop profile
        business_name = request.POST.get('business_name')
        business_description = request.POST.get('business_description')
        business_email = request.POST.get('business_email')
        business_phone = request.POST.get('business_phone')
        business_address = request.POST.get('business_address')
        business_city = request.POST.get('business_city')
        website_theme = request.POST.get('website_theme', 'default')
        
        if not all([business_name, business_description, business_email, business_phone, business_address, business_city]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'shop_website/setup_website.html')
        
        shop_profile = ShopProfile.objects.create(
            user_profile=profile,
            business_name=business_name,
            business_description=business_description,
            business_email=business_email,
            business_phone=business_phone,
            business_address=business_address,
            business_city=business_city,
            website_theme=website_theme
        )
        
        messages.success(request, f'Website for "{business_name}" has been setup successfully!')
        return redirect('shop_website:edit_website')
    
    return render(request, 'shop_website/setup_website.html')


@login_required
def edit_website(request):
    """Edit website settings"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can edit websites.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
    except ShopProfile.DoesNotExist:
        return redirect('shop_website:setup_website')
    
    if request.method == 'POST':
        # Update shop profile
        shop_profile.business_name = request.POST.get('business_name')
        shop_profile.business_description = request.POST.get('business_description')
        shop_profile.business_email = request.POST.get('business_email')
        shop_profile.business_phone = request.POST.get('business_phone')
        shop_profile.business_address = request.POST.get('business_address')
        shop_profile.business_city = request.POST.get('business_city')
        shop_profile.website_theme = request.POST.get('website_theme', 'default')
        shop_profile.is_website_active = request.POST.get('is_website_active') == 'on'
        
        if request.FILES.get('logo'):
            shop_profile.logo = request.FILES.get('logo')
        
        if all([shop_profile.business_name, shop_profile.business_description, 
                shop_profile.business_email, shop_profile.business_phone, 
                shop_profile.business_address, shop_profile.business_city]):
            shop_profile.save()
            messages.success(request, 'Website settings updated successfully!')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    return render(request, 'shop_website/edit_website.html', {'shop_profile': shop_profile})


@login_required
def manage_products(request):
    """Manage website products"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can manage products.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
    except ShopProfile.DoesNotExist:
        messages.error(request, 'Please setup your website first.')
        return redirect('shop_website:setup_website')
    
    products = ShopProduct.objects.filter(shop_profile=shop_profile).order_by('-created_at')
    
    return render(request, 'shop_website/manage_products.html', {
        'shop_profile': shop_profile,
        'products': products
    })


@login_required
def add_product(request):
    """Add product to website"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can add products.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
    except ShopProfile.DoesNotExist:
        messages.error(request, 'Please setup your website first.')
        return redirect('shop_website:setup_website')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        original_price = request.POST.get('original_price')
        category = request.POST.get('category')
        tags = request.POST.get('tags')
        stock_quantity = request.POST.get('stock_quantity')
        is_featured = request.POST.get('is_featured') == 'on'
        is_available = request.POST.get('is_available') == 'on'
        
        if not all([name, description, price, category, stock_quantity]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'shop_website/add_product.html', {'shop_profile': shop_profile})
        
        try:
            price = Decimal(price)
            stock_quantity = int(stock_quantity)
            if original_price:
                original_price = Decimal(original_price)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid price or stock quantity.')
            return render(request, 'shop_website/add_product.html', {'shop_profile': shop_profile})
        
        if not request.FILES.get('image'):
            messages.error(request, 'Please upload a product image.')
            return render(request, 'shop_website/add_product.html', {'shop_profile': shop_profile})
        
        product = ShopProduct.objects.create(
            shop_profile=shop_profile,
            name=name,
            description=description,
            price=price,
            original_price=original_price if original_price else None,
            category=category,
            tags=tags,
            stock_quantity=stock_quantity,
            is_featured=is_featured,
            is_available=is_available,
            image=request.FILES.get('image')
        )
        
        messages.success(request, f'Product "{name}" has been added to your website!')
        return redirect('shop_website:manage_products')
    
    return render(request, 'shop_website/add_product.html', {'shop_profile': shop_profile})


@login_required
def edit_product(request, product_id):
    """Edit website product"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can edit products.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
        product = ShopProduct.objects.get(id=product_id, shop_profile=shop_profile)
    except (ShopProfile.DoesNotExist, ShopProduct.DoesNotExist):
        messages.error(request, 'Product not found.')
        return redirect('shop_website:manage_products')
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.original_price = request.POST.get('original_price')
        product.category = request.POST.get('category')
        product.tags = request.POST.get('tags')
        product.stock_quantity = request.POST.get('stock_quantity')
        product.is_featured = request.POST.get('is_featured') == 'on'
        product.is_available = request.POST.get('is_available') == 'on'
        
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        
        if all([product.name, product.description, product.price, product.category, product.stock_quantity]):
            try:
                product.price = Decimal(product.price)
                product.stock_quantity = int(product.stock_quantity)
                if product.original_price:
                    product.original_price = Decimal(product.original_price)
                product.save()
                messages.success(request, f'Product "{product.name}" has been updated!')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid price or stock quantity.')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    return render(request, 'shop_website/edit_product.html', {
        'shop_profile': shop_profile,
        'product': product
    })


@login_required
def delete_product(request, product_id):
    """Delete website product"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can delete products.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
        product = ShopProduct.objects.get(id=product_id, shop_profile=shop_profile)
    except (ShopProfile.DoesNotExist, ShopProduct.DoesNotExist):
        messages.error(request, 'Product not found.')
        return redirect('shop_website:manage_products')
    
    # Check if product is referenced in any active carts or orders
    from shop_website.models import CartItem, OrderItem
    
    cart_items = CartItem.objects.filter(product=product)
    order_items = OrderItem.objects.filter(product=product)
    
    if request.method == 'POST':
        try:
            product_name = product.name
            
            # Delete related cart items first
            cart_items.delete()
            
            # Check if product is in any completed orders (not cancelled)
            active_orders = order_items.filter(order__order_status__in=['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED', 'SIGNED'])
            
            if active_orders.exists():
                messages.error(request, f'Cannot delete "{product_name}" because it is referenced in active orders. Please cancel or complete those orders first.')
                return render(request, 'shop_website/delete_product.html', {
                    'shop_profile': shop_profile,
                    'product': product,
                    'has_active_orders': True,
                    'active_orders_count': active_orders.count()
                })
            
            # Delete order items from cancelled orders
            order_items.delete()
            
            # Finally delete the product
            product.delete()
            messages.success(request, f'Product "{product_name}" has been deleted from your website!')
            return redirect('shop_website:manage_products')
            
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
            return render(request, 'shop_website/delete_product.html', {
                'shop_profile': shop_profile,
                'product': product
            })
    
    return render(request, 'shop_website/delete_product.html', {
        'shop_profile': shop_profile,
        'product': product,
        'cart_items_count': cart_items.count(),
        'order_items_count': order_items.count()
    })


@login_required
def manage_orders(request):
    """Manage website orders"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can manage orders.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
    except ShopProfile.DoesNotExist:
        messages.error(request, 'Please setup your website first.')
        return redirect('shop_website:setup_website')
    
    orders = shop_profile.orders.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    # Prepare orders data for JavaScript
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'order_status': order.order_status,
            'customer_signature': bool(order.customer_signature)
        })
    
    return render(request, 'shop_website/manage_orders.html', {
        'shop_profile': shop_profile,
        'orders': orders,
        'orders_json': json.dumps(orders_data),
        'status_choices': Order.ORDER_STATUS_CHOICES,
        'current_status': status_filter
    })


@login_required
def update_order_status(request, order_id):
    """Update order status"""
    profile = get_user_profile(request.user)
    if not profile.is_shop_admin:
        messages.error(request, 'Access denied. Only shop administrators can update orders.')
        return redirect('users:shop_admin_dashboard')
    
    try:
        shop_profile = profile.shop_website
        order = shop_profile.orders.get(id=order_id)
    except (ShopProfile.DoesNotExist, Order.DoesNotExist):
        messages.error(request, 'Order not found.')
        return redirect('shop_website:manage_orders')
    
    if request.method == 'POST':
        new_status = request.POST.get('order_status')
        
        if new_status in dict(order.ORDER_STATUS_CHOICES).keys():
            order.order_status = new_status
            order.save()
            messages.success(request, f'Order {order.order_number} status updated to {order.get_order_status_display()}.')
        else:
            messages.error(request, f'Invalid status selected. Received: {new_status}')
    
    return redirect('shop_website:manage_orders')


@csrf_exempt
@require_POST
@login_required
def save_signature(request):
    """Save customer signature for an order"""
    try:
        order_id = request.POST.get('order_id')
        signature_data = request.POST.get('signature')
        
        if not order_id or not signature_data:
            return JsonResponse({'success': False, 'error': 'Missing required data'})
        
        # Get user profile and verify shop admin
        profile = get_user_profile(request.user)
        if not profile.is_shop_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        # Get order
        order = get_object_or_404(Order, id=order_id, shop_profile__user_profile=profile)
        
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
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
