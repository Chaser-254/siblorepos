from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_request, name='register_request'),
    path('site-admin/', views.site_owner_dashboard, name='site_owner_dashboard'),
    path('shop-admin/', views.shop_admin_dashboard, name='shop_admin_dashboard'),
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('cashier/orders/', views.cashier_orders, name='cashier_orders'),
    path('cashier/orders/<int:pk>/', views.cashier_order_detail, name='cashier_order_detail'),
    path('cashier/orders/<int:pk>/update/', views.cashier_update_order_status, name='cashier_update_order_status'),
    path('cashier/save-signature/', views.cashier_save_signature, name='cashier_save_signature'),
    path('requests/', views.registration_requests, name='registration_requests'),
    path('requests/<int:pk>/update/', views.update_request_status, name='update_request_status'),
    path('requests/<int:pk>/delete/', views.delete_request, name='delete_request'),
    path('cashiers/', views.cashier_list, name='cashier_list'),
    path('cashiers/create/', views.cashier_create, name='cashier_create'),
    path('cashiers/<int:pk>/update/', views.cashier_update, name='cashier_update'),
    path('cashiers/<int:pk>/toggle-active/', views.cashier_toggle_active, name='cashier_toggle_active'),
    path('dashboard/', views.user_list, name='user_list'),
    path('business-details/', views.business_details, name='business_details'),
    path('create/', views.user_create, name='user_create'),
    path('user/<int:pk>/update/', views.user_update, name='user_update'),
    path('user/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
]
