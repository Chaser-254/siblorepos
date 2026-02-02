from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, Http404, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
import json

from .pdf_utils import generate_invoice_pdf as generate_reportlab_pdf
from .models import Invoice, InvoiceItem, InvoicePayment, InvoiceTemplate
from .forms import InvoiceForm, InvoiceItemForm, InvoicePaymentForm
from sales.models import Customer
from products.models import Product


class InvoiceAccessMixin:
    """Mixin to ensure invoice access security"""
    
    def get_invoice_queryset(self):
        user = self.request.user
        profile = user.profile
        
        if profile.is_site_admin:
            return Invoice.objects.all()
        elif profile.is_shop_admin:
            return Invoice.objects.filter(shop_admin=profile)
        elif profile.is_cashier:
            return Invoice.objects.filter(shop_admin=profile.shop_admin)
        else:
            return Invoice.objects.none()
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_be_accessed_by(self.request.user):
            raise PermissionDenied("You don't have permission to access this invoice.")
        return obj


class InvoiceListView(LoginRequiredMixin, ListView):
    """List invoices with tenant filtering"""
    model = Invoice
    template_name = 'invoicing/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        profile = user.profile
        
        # Apply tenant filtering
        if profile.is_site_admin:
            queryset = Invoice.objects.all()
        elif profile.is_shop_admin:
            queryset = Invoice.objects.filter(shop_admin=profile)
        elif profile.is_cashier:
            queryset = Invoice.objects.filter(shop_admin=profile.shop_admin)
        else:
            queryset = Invoice.objects.none()
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        customer_filter = self.request.GET.get('customer')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        search = self.request.GET.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if customer_filter:
            queryset = queryset.filter(customer_id=customer_filter)
        
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)
        
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(customer__email__icontains=search)
            )
        
        return queryset.select_related('customer', 'shop_admin').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile
        
        # Get filter options
        if profile.is_site_admin:
            customers = Customer.objects.all()
        elif profile.is_shop_admin:
            customers = Customer.objects.filter(shop_admin=profile)
        elif profile.is_cashier:
            customers = Customer.objects.filter(shop_admin=profile.shop_admin)
        else:
            customers = Customer.objects.none()
        
        context.update({
            'status_choices': Invoice.STATUS_CHOICES,
            'customers': customers,
            'stats': {
                'total_invoices': self.get_queryset().count(),
                'total_amount': self.get_queryset().aggregate(
                    total=Sum('total_amount')
                )['total'] or 0,
                'paid_amount': self.get_queryset().filter(
                    status='PAID'
                ).aggregate(total=Sum('total_amount'))['total'] or 0,
                'pending_amount': self.get_queryset().filter(
                    status__in=['DRAFT', 'SENT', 'PARTIALLY_PAID']
                ).aggregate(
                    total=Sum('total_amount') - Sum('amount_paid')
                )['total'] or 0,
            },
            'status_breakdown': self.get_queryset().values('status').annotate(
                count=Count('id'),
                amount=Sum('total_amount')
            ).order_by('status'),
            'recent_invoices': self.get_queryset().select_related('customer').order_by('-created_at')[:10],
        })
        
        return context


class InvoiceDetailView(LoginRequiredMixin, InvoiceAccessMixin, DetailView):
    """Invoice detail view with security checks"""
    model = Invoice
    template_name = 'invoicing/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        
        context.update({
            'items': invoice.items.select_related('product'),
            'payments': invoice.payments.all().order_by('-created_at'),
            'payment_form': InvoicePaymentForm(),
            'can_edit': invoice.status in ['DRAFT'] and self.request.user.profile.can_manage_products,
            'can_delete': invoice.status in ['DRAFT'] and self.request.user.profile.can_delete_sales,
        })
        
        return context


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    """Create new invoice with tenant assignment"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoicing/invoice_form.html'
    success_url = reverse_lazy('invoicing:invoice_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Set shop_admin based on user role
        user_profile = self.request.user.profile
        if user_profile.is_site_admin:
            # For site admins, get the first shop admin or require selection
            from users.models import UserProfile
            first_shop_admin = UserProfile.objects.filter(is_shop_admin=True).first()
            if first_shop_admin:
                form.instance.shop_admin = first_shop_admin
            else:
                messages.error(self.request, 'No shop admin found. Please create a shop admin first.')
                return self.form_invalid(form)
        elif user_profile.is_shop_admin:
            form.instance.shop_admin = user_profile
        elif user_profile.is_cashier:
            form.instance.shop_admin = user_profile.shop_admin
        
        # Save the invoice first
        response = super().form_valid(form)
        invoice = self.object
        
        # Process invoice items
        item_descriptions = self.request.POST.getlist('item_description[]')
        item_quantities = self.request.POST.getlist('item_quantity[]')
        item_unit_prices = self.request.POST.getlist('item_unit_price[]')
        item_discounts = self.request.POST.getlist('item_discount[]')
        item_products = self.request.POST.getlist('item_product[]')
        item_ids = self.request.POST.getlist('item_id[]')
        
        # Create new items
        for i, description in enumerate(item_descriptions):
            if description and description.strip() and i < len(item_quantities):
                try:
                    quantity = float(item_quantities[i]) if item_quantities[i] and item_quantities[i].strip() else 0
                    unit_price = float(item_unit_prices[i]) if item_unit_prices[i] and item_unit_prices[i].strip() else 0
                    discount_rate = float(item_discounts[i]) if item_discounts[i] and item_discounts[i].strip() else 0
                    product_id = item_products[i] if i < len(item_products) and item_products[i] and item_products[i].strip() else None
                    
                    if quantity > 0 and unit_price > 0:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=description,
                            quantity=quantity,
                            unit_price=unit_price,
                            discount_rate=discount_rate,
                            product_id=product_id if product_id else None
                        )
                except (ValueError, IndexError):
                    continue  # Skip invalid data
        
        # Update invoice totals
        update_invoice_totals(invoice)
        
        messages.success(self.request, 'Invoice created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile
        
        # Get available customers and products
        if profile.is_site_admin:
            customers = Customer.objects.all()
            products = Product.objects.all()
        elif profile.is_shop_admin:
            customers = Customer.objects.filter(shop_admin=profile)
            products = Product.objects.filter(shop_admin=profile)
        elif profile.is_cashier:
            customers = Customer.objects.filter(shop_admin=profile.shop_admin)
            products = Product.objects.filter(shop_admin=profile.shop_admin)
        else:
            customers = Customer.objects.none()
            products = Product.objects.none()
        
        context.update({
            'customers': customers,
            'products': products,
            'item_form': InvoiceItemForm(),
        })
        
        return context


class InvoiceUpdateView(LoginRequiredMixin, InvoiceAccessMixin, UpdateView):
    """Update invoice with security checks"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoicing/invoice_form.html'
    success_url = reverse_lazy('invoicing:invoice_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        
        if invoice.status not in ['DRAFT']:
            messages.warning(self.request, 'This invoice cannot be edited anymore.')
        
        context.update({
            'items': invoice.items.all(),
            'customers': Customer.objects.filter(
                shop_admin=invoice.shop_admin
            ),
            'products': Product.objects.filter(
                shop_admin=invoice.shop_admin
            ),
            'item_form': InvoiceItemForm(),
        })
        
        return context
    
    def form_valid(self, form):
        # Save the invoice first
        response = super().form_valid(form)
        invoice = self.object
        
        # Process invoice items
        item_descriptions = self.request.POST.getlist('item_description[]')
        item_quantities = self.request.POST.getlist('item_quantity[]')
        item_unit_prices = self.request.POST.getlist('item_unit_price[]')
        item_discounts = self.request.POST.getlist('item_discount[]')
        item_products = self.request.POST.getlist('item_product[]')
        item_ids = self.request.POST.getlist('item_id[]')
        
        # Clear existing items and create new ones
        invoice.items.all().delete()
        
        for i, description in enumerate(item_descriptions):
            if description and description.strip() and i < len(item_quantities):
                try:
                    quantity = float(item_quantities[i]) if item_quantities[i] and item_quantities[i].strip() else 0
                    unit_price = float(item_unit_prices[i]) if item_unit_prices[i] and item_unit_prices[i].strip() else 0
                    discount_rate = float(item_discounts[i]) if item_discounts[i] and item_discounts[i].strip() else 0
                    product_id = item_products[i] if i < len(item_products) and item_products[i] and item_products[i].strip() else None
                    
                    if quantity > 0 and unit_price > 0:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=description,
                            quantity=quantity,
                            unit_price=unit_price,
                            discount_rate=discount_rate,
                            product_id=product_id if product_id else None
                        )
                except (ValueError, IndexError):
                    continue  # Skip invalid data
        
        # Update invoice totals
        update_invoice_totals(invoice)
        
        messages.success(self.request, 'Invoice updated successfully!')
        return response


class InvoiceDeleteView(LoginRequiredMixin, InvoiceAccessMixin, DeleteView):
    """Delete invoice with security checks"""
    model = Invoice
    template_name = 'invoicing/invoice_confirm_delete.html'
    success_url = reverse_lazy('invoicing:invoice_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        user_profile = self.request.user.profile
        
        # Determine if invoice can be deleted and what warnings to show
        can_delete = True
        deletion_warnings = []
        
        if invoice.status == 'PAID':
            if not user_profile.is_site_admin:
                can_delete = False
                deletion_warnings.append("Paid invoices can only be deleted by site administrators.")
            else:
                deletion_warnings.append("This is a PAID invoice. Deleting it will remove all payment records.")
        elif invoice.status in ['SENT', 'PARTIALLY_PAID']:
            if invoice.payments.exists():
                deletion_warnings.append(f"This invoice has {invoice.payments.count()} payment record(s) that will be deleted.")
            deletion_warnings.append("This invoice has been sent to the customer. Consider cancelling instead of deleting.")
        elif invoice.status == 'OVERDUE':
            deletion_warnings.append("This is an overdue invoice. Deleting it will remove all debt tracking.")
        elif invoice.status == 'CANCELLED':
            deletion_warnings.append("This invoice is already cancelled.")
        
        context.update({
            'can_delete': can_delete,
            'deletion_warnings': deletion_warnings,
            'has_payments': invoice.payments.exists(),
            'payment_count': invoice.payments.count(),
        })
        
        return context
    
    def delete(self, request, *args, **kwargs):
        invoice = self.get_object()
        user_profile = request.user.profile
        
        # Check if invoice can be deleted based on user role and status
        if invoice.status == 'PAID' and not user_profile.is_site_admin:
            messages.error(request, 'Only site administrators can delete paid invoices.')
            return redirect('invoicing:invoice_detail', pk=invoice.pk)
        
        # Additional confirmation for invoices with payments
        if invoice.payments.exists():
            confirm_payment_delete = request.POST.get('confirm_payment_delete', '')
            if confirm_payment_delete != invoice.invoice_number:
                messages.error(request, f'Please type the invoice number "{invoice.invoice_number}" to confirm deletion of payments.')
                return redirect('invoicing:invoice_detail', pk=invoice.pk)
        
        messages.success(request, f'Invoice #{invoice.invoice_number} deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def add_invoice_item(request, invoice_id):
    """Add item to invoice with security checks"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if not invoice.can_be_accessed_by(request.user):
        raise PermissionDenied("You don't have permission to modify this invoice.")
    
    if invoice.status not in ['DRAFT']:
        return JsonResponse({'error': 'Cannot add items to this invoice'}, status=400)
    
    if request.method == 'POST':
        form = InvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.invoice = invoice
            
            # Validate product belongs to same tenant
            if not item.product.shop_admin == invoice.shop_admin:
                return JsonResponse({'error': 'Product does not belong to this shop'}, status=400)
            
            item.save()
            
            # Update invoice totals
            update_invoice_totals(invoice)
            
            return JsonResponse({
                'success': True,
                'item_id': item.id,
                'item_html': render_invoice_item(item),
                'subtotal': float(invoice.subtotal),
                'tax_amount': float(invoice.tax_amount),
                'total_amount': float(invoice.total_amount),
            })
        else:
            return JsonResponse({'error': form.errors}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def delete_invoice_item(request, item_id):
    """Delete invoice item with security checks"""
    item = get_object_or_404(InvoiceItem, id=item_id)
    invoice = item.invoice
    
    if not invoice.can_be_accessed_by(request.user):
        raise PermissionDenied("You don't have permission to modify this invoice.")
    
    if invoice.status not in ['DRAFT']:
        return JsonResponse({'error': 'Cannot delete items from this invoice'}, status=400)
    
    item.delete()
    update_invoice_totals(invoice)
    
    return JsonResponse({
        'success': True,
        'subtotal': float(invoice.subtotal),
        'tax_amount': float(invoice.tax_amount),
        'total_amount': float(invoice.total_amount),
    })


@login_required
def add_invoice_payment(request, invoice_id):
    """Add payment to invoice with security checks"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if not invoice.can_be_accessed_by(request.user):
        raise PermissionDenied("You don't have permission to modify this invoice.")
    
    if request.method == 'POST':
        form = InvoicePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.created_by = request.user
            payment.save()
            
            messages.success(request, 'Payment added successfully!')
            return redirect('invoicing:invoice_detail', pk=invoice.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    
    return redirect('invoicing:invoice_detail', pk=invoice_id)


def public_invoice_view(request, uuid):
    """Public invoice view for customers with secure access"""
    try:
        invoice = Invoice.objects.get(uuid=uuid)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")
    
    # Log access for security
    context = {
        'invoice': invoice,
        'items': invoice.items.select_related('product'),
        'payments': invoice.payments.all().order_by('-created_at'),
        'is_public_view': True,
    }
    
    return render(request, 'invoicing/public_invoice.html', context)


@login_required
def generate_invoice_pdf(request, invoice_id):
    """Generate PDF invoice with security checks using ReportLab"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if not invoice.can_be_accessed_by(request.user):
        raise PermissionDenied("You don't have permission to access this invoice.")
    
    # Get template
    template = InvoiceTemplate.objects.filter(
        shop_admin=invoice.shop_admin,
        is_default=True
    ).first()
    
    # Get related data
    items = invoice.items.select_related('product').all()
    payments = invoice.payments.all().order_by('-created_at')
    
    # Generate PDF using ReportLab
    try:
        pdf_data = generate_reportlab_pdf(invoice, items, payments, template)
        
        # Create HTTP response
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        return response
        
    except Exception as e:
        # Fallback to HTML if PDF generation fails
        context = {
            'invoice': invoice,
            'items': items,
            'payments': payments,
            'template': template,
            'pdf_mode': True,
            'error': str(e)
        }
        
        response = render(request, 'invoicing/invoice_pdf.html', context)
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.html"'
        return response


def update_invoice_totals(invoice):
    """Update invoice totals based on items"""
    items_total = invoice.items.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    invoice.subtotal = items_total
    invoice.save()


def render_invoice_item(item):
    """Render invoice item HTML"""
    return render_to_string('invoicing/partials/invoice_item.html', {'item': item})


@login_required
def invoice_dashboard(request):
    """Invoice dashboard with statistics"""
    user = request.user
    profile = user.profile
    
    # Get base queryset
    if profile.is_site_admin:
        invoices = Invoice.objects.all()
    elif profile.is_shop_admin:
        invoices = Invoice.objects.filter(shop_admin=profile)
    elif profile.is_cashier:
        invoices = Invoice.objects.filter(shop_admin=profile.shop_admin)
    else:
        invoices = Invoice.objects.none()
    
    # Calculate statistics
    stats = {
        'total_invoices': invoices.count(),
        'total_amount': invoices.aggregate(total=Sum('total_amount'))['total'] or 0,
        'paid_amount': invoices.filter(status='PAID').aggregate(
            total=Sum('total_amount')
        )['total'] or 0,
        'pending_amount': invoices.filter(
            status__in=['DRAFT', 'SENT', 'PARTIALLY_PAID']
        ).aggregate(
            total=Sum('total_amount') - Sum('amount_paid')
        )['total'] or 0,
        'overdue_amount': invoices.filter(status='OVERDUE').aggregate(
            total=Sum('total_amount') - Sum('amount_paid')
        )['total'] or 0,
    }
    
    # Recent invoices
    recent_invoices = invoices.select_related('customer').order_by('-created_at')[:10]
    
    # Status breakdown
    status_breakdown = invoices.values('status').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('status')
    
    context = {
        'stats': stats,
        'recent_invoices': recent_invoices,
        'status_breakdown': status_breakdown,
    }
    
    return render(request, 'invoicing/dashboard.html', context)
