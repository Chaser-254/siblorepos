from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('pos/', views.pos_terminal, name='pos_terminal'),
    path('process-sale/', views.process_sale, name='process_sale'),
    
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    path('sales/<int:pk>/delete/', views.sale_delete, name='sale_delete'),
    
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    
    path('debts/', views.debts_list, name='debts_list'),
    path('debts/<int:pk>/pay/', views.pay_debt, name='pay_debt'),
    
    path('reports/', views.reports, name='reports'),
    path('reports/print/', views.report_print, name='report_print'),
]
