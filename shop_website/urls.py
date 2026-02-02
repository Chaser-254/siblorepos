from django.urls import path
from . import views
from . import admin_views

app_name = 'shop_website'

urlpatterns = [
    # Public shop URLs
    path('shop/<str:username>/', views.shop_home, name='shop_home'),
    path('shop/<str:username>/products/', views.shop_products, name='shop_products'),
    path('shop/<str:username>/product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('shop/<str:username>/cart/', views.cart_view, name='cart'),
    path('shop/<str:username>/checkout/', views.checkout, name='checkout'),
    path('shop/<str:username>/order/success/<str:order_number>/', views.order_success, name='order_success'),
    
    # AJAX cart operations
    path('shop/<str:username>/cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('shop/<str:username>/cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('shop/<str:username>/cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Shop admin URLs
    path('shop/admin/dashboard/', views.shop_admin_dashboard, name='shop_admin_dashboard'),
    
    # Website management URLs
    path('shop/admin/setup/', admin_views.setup_website, name='setup_website'),
    path('shop/admin/edit/', admin_views.edit_website, name='edit_website'),
    path('shop/admin/products/', admin_views.manage_products, name='manage_products'),
    path('shop/admin/products/add/', admin_views.add_product, name='add_product'),
    path('shop/admin/products/<int:product_id>/edit/', admin_views.edit_product, name='edit_product'),
    path('shop/admin/products/<int:product_id>/delete/', admin_views.delete_product, name='delete_product'),
    path('shop/admin/orders/', admin_views.manage_orders, name='manage_orders'),
    path('shop/admin/orders/<int:order_id>/status/', admin_views.update_order_status, name='update_order_status'),
    path('shop/admin/save-signature/', admin_views.save_signature, name='save_signature'),
    
    # Customer portal URLs
    path('customer/lookup/', views.customer_order_lookup, name='customer_order_lookup'),
    path('customer/order/<str:order_number>/', views.customer_order_detail, name='customer_order_detail'),
    path('customer/save-signature/<str:order_number>/', views.customer_save_signature, name='customer_save_signature'),
    path('customer/search/', views.customer_order_search, name='customer_order_search'),
]
