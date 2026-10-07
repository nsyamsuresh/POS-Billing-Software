from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from accounts.mixins import AdminRequiredMixin
from .forms import SupplierForm, ProductForm
from .models import Supplier, Product

class SafeDeleteMixin:
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Cannot delete: it is used in bills or purchases. For a product, untick Active instead.')
            return redirect(self.success_url)
        messages.success(self.request, 'Deleted.')
        return response

# Suppliers
class SupplierList(AdminRequiredMixin, ListView):
    model = Supplier
    template_name = 'catalog/supplier_list.html'
    context_object_name = 'suppliers'
    ordering = ['name']

class SupplierCreate(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('supplier_list')
    success_message = 'Supplier saved.'
    extra_context = {'title': 'Add supplier', 'back': 'supplier_list'}

class SupplierUpdate(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('supplier_list')
    success_message = 'Supplier updated.'
    extra_context = {'title': 'Edit supplier', 'back': 'supplier_list'}

class SupplierDelete(AdminRequiredMixin, SafeDeleteMixin, DeleteView):
    model = Supplier
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('supplier_list')
    extra_context = {'back': 'supplier_list'}

# Products
class ProductList(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.select_related('supplier').order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(barcode__icontains=q) | Q(category__icontains=q))
        if self.request.GET.get('low'):
            qs = qs.filter(stock__lte=F('low_stock_level'))
        return qs

class ProductCreate(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('product_list')
    success_message = 'Product saved.'
    extra_context = {'title': 'Add product', 'back': 'product_list'}

class ProductUpdate(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('product_list')
    success_message = 'Product updated.'
    extra_context = {'title': 'Edit product', 'back': 'product_list'}

class ProductDelete(AdminRequiredMixin, SafeDeleteMixin, DeleteView):
    model = Product
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('product_list')
    extra_context = {'back': 'product_list'}