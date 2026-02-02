from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.invoice_dashboard, name='dashboard'),
    
    # Invoice CRUD
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
    path('create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    
    # Invoice items
    path('<int:invoice_id>/add-item/', views.add_invoice_item, name='add_invoice_item'),
    path('item/<int:item_id>/delete/', views.delete_invoice_item, name='delete_invoice_item'),
    
    # Invoice payments
    path('<int:invoice_id>/add-payment/', views.add_invoice_payment, name='add_invoice_payment'),
    
    # PDF generation
    path('<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),
    
    # Public access (for customers)
    path('public/<uuid:uuid>/', views.public_invoice_view, name='public_invoice'),
]
