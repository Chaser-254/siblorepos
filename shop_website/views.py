from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import uuid
import json

from .models import ShopProfile, ShopProduct, Cart, CartItem, Order, OrderItem
from users.models import UserProfile


def shop_home(request, username):
    """Public shop homepage"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
    except UserProfile.DoesNotExist:
        raise Http404("Shop not found")
    
    # Get featured products and recent products
    featured_products = ShopProduct.objects.filter(
        shop_profile=shop_profile, 
        is_featured=True, 
        is_available=True,
        stock_quantity__gt=0
    )[:6]
    
    recent_products = ShopProduct.objects.filter(
        shop_profile=shop_profile,
        is_available=True,
        stock_quantity__gt=0
    ).order_by('-created_at')[:12]
    
    # Get cart from session
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    cart = None
    cart_items_count = 0
    
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
            cart_items_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    context = {
        'shop_profile': shop_profile,
        'featured_products': featured_products,
        'recent_products': recent_products,
        'cart': cart,
        'cart_items_count': cart_items_count,
    }
    
    return render(request, 'shop_website/shop_home.html', context)


def shop_products(request, username):
    """Shop products listing page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
    except UserProfile.DoesNotExist:
        raise Http404("Shop not found")
    
    products = ShopProduct.objects.filter(
        shop_profile=shop_profile,
        is_available=True,
        stock_quantity__gt=0
    )
    
    # Search functionality
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    if category:
        products = products.filter(category__icontains=category)
    
    # Get categories for filter
    categories = ShopProduct.objects.filter(
        shop_profile=shop_profile
    ).values_list('category', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get cart info
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    cart = None
    cart_items_count = 0
    
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
            cart_items_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    context = {
        'shop_profile': shop_profile,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category,
        'cart': cart,
        'cart_items_count': cart_items_count,
    }
    
    return render(request, 'shop_website/shop_products.html', context)


def product_detail(request, username, product_id):
    """Product detail page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
        product = get_object_or_404(ShopProduct, id=product_id, shop_profile=shop_profile)
    except (UserProfile.DoesNotExist, ShopProduct.DoesNotExist):
        raise Http404("Product not found")
    
    # Get related products
    related_products = ShopProduct.objects.filter(
        shop_profile=shop_profile,
        category=product.category,
        is_available=True,
        stock_quantity__gt=0
    ).exclude(id=product.id)[:4]
    
    # Get cart info
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    cart = None
    cart_items_count = 0
    
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
            cart_items_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    context = {
        'shop_profile': shop_profile,
        'product': product,
        'related_products': related_products,
        'cart': cart,
        'cart_items_count': cart_items_count,
    }
    
    return render(request, 'shop_website/product_detail.html', context)


@require_POST
def add_to_cart(request, username, product_id):
    """Add product to cart"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
        product = get_object_or_404(ShopProduct, id=product_id, shop_profile=shop_profile)
    except (UserProfile.DoesNotExist, ShopProduct.DoesNotExist):
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > product.stock_quantity:
        return JsonResponse({'error': 'Not enough stock available'}, status=400)
    
    # Get or create cart
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    
    if not cart_id:
        cart_id = str(uuid.uuid4())
        request.session[f'cart_{shop_profile.id}'] = cart_id
        cart = Cart.objects.create(
            cart_id=cart_id,
            shop_profile=shop_profile
        )
    else:
        cart, created = Cart.objects.get_or_create(
            cart_id=cart_id,
            shop_profile=shop_profile
        )
    
    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            return JsonResponse({'error': 'Not enough stock available'}, status=400)
        cart_item.quantity = new_quantity
        cart_item.save()
    
    return JsonResponse({
        'success': True,
        'message': f'{product.name} added to cart',
        'cart_items_count': cart.total_items,
        'cart_total': str(cart.total_price)
    })


def cart_view(request, username):
    """Shopping cart page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
    except UserProfile.DoesNotExist:
        raise Http404("Shop not found")
    
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    cart = None
    
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            pass
    
    if not cart or cart.is_empty:
        context = {
            'shop_profile': shop_profile,
            'cart': None,
            'cart_items_count': 0,
        }
        return render(request, 'shop_website/empty_cart.html', context)
    
    context = {
        'shop_profile': shop_profile,
        'cart': cart,
        'cart_items_count': cart.total_items,
    }
    
    return render(request, 'shop_website/cart.html', context)


@require_POST
def update_cart(request, username, item_id):
    """Update cart item quantity"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__shop_profile=shop_profile)
    except (UserProfile.DoesNotExist, CartItem.DoesNotExist):
        return JsonResponse({'error': 'Cart item not found'}, status=404)
    
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > cart_item.product.stock_quantity:
        return JsonResponse({'error': 'Not enough stock available'}, status=400)
    
    if quantity <= 0:
        cart_item.delete()
    else:
        cart_item.quantity = quantity
        cart_item.save()
    
    cart = cart_item.cart
    return JsonResponse({
        'success': True,
        'cart_items_count': cart.total_items,
        'cart_total': str(cart.total_price),
        'item_subtotal': str(cart_item.subtotal) if quantity > 0 else '0.00'
    })


@require_POST
def remove_from_cart(request, username, item_id):
    """Remove item from cart"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__shop_profile=shop_profile)
    except (UserProfile.DoesNotExist, CartItem.DoesNotExist):
        return JsonResponse({'error': 'Cart item not found'}, status=404)
    
    cart = cart_item.cart
    cart_item.delete()
    
    return JsonResponse({
        'success': True,
        'cart_items_count': cart.total_items,
        'cart_total': str(cart.total_price)
    })


def checkout(request, username):
    """Checkout page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
    except UserProfile.DoesNotExist:
        raise Http404("Shop not found")
    
    cart_id = request.session.get(f'cart_{shop_profile.id}')
    cart = None
    
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            pass
    
    if not cart or cart.is_empty:
        return redirect('shop_website:cart', username=username)
    
    if request.method == 'POST':
        # Process order
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_phone = request.POST.get('customer_phone')
        delivery_address = request.POST.get('delivery_address', '')
        notes = request.POST.get('notes', '')
        
        if not all([customer_name, customer_email, customer_phone]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('shop_website:checkout', username=username)
        
        # Create order
        order = Order.objects.create(
            shop_profile=shop_profile,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            notes=notes,
            subtotal=cart.total_price,
            total_amount=cart.total_price
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                subtotal=cart_item.subtotal
            )
            
            # Update product stock
            product = cart_item.product
            product.stock_quantity -= cart_item.quantity
            product.save()
        
        # Clear cart
        cart.items.all().delete()
        
        messages.success(request, f'Order {order.order_number} placed successfully!')
        return redirect('shop_website:order_success', username=username, order_number=order.order_number)
    
    context = {
        'shop_profile': shop_profile,
        'cart': cart,
        'cart_items_count': cart.total_items,
    }
    
    return render(request, 'shop_website/checkout.html', context)


def order_success(request, username, order_number):
    """Order success page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username, role='SHOP_ADMIN')
        shop_profile = get_object_or_404(ShopProfile, user_profile=user_profile, is_website_active=True)
        order = get_object_or_404(Order, order_number=order_number, shop_profile=shop_profile)
    except (UserProfile.DoesNotExist, Order.DoesNotExist):
        raise Http404("Order not found")
    
    context = {
        'shop_profile': shop_profile,
        'order': order,
    }
    
    return render(request, 'shop_website/order_success.html', context)


# Admin views for shop management
@login_required
def shop_admin_dashboard(request):
    """Shop admin dashboard for managing website"""
    if not request.user.profile.is_shop_admin:
        messages.error(request, 'Access denied. Shop admin only.')
        return redirect('home')
    
    try:
        shop_profile = request.user.profile.shop_website
    except ShopProfile.DoesNotExist:
        shop_profile = None
    
    if shop_profile:
        products_count = ShopProduct.objects.filter(shop_profile=shop_profile).count()
        orders_count = Order.objects.filter(shop_profile=shop_profile).count()
        recent_orders = Order.objects.filter(shop_profile=shop_profile).order_by('-created_at')[:5]
    else:
        products_count = 0
        orders_count = 0
        recent_orders = []
    
    context = {
        'shop_profile': shop_profile,
        'products_count': products_count,
        'orders_count': orders_count,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'shop_website/shop_admin_dashboard.html', context)
