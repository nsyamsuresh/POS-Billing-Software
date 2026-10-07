from accounts.decorators import admin_required
from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm, SupplierForm
from .models import Product, Supplier


# ---------- Products ----------

@admin_required
def product_list(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.select_related('supplier').order_by('name')
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(barcode__icontains=q) | Q(category__icontains=q))
    return render(request, 'catalog/product_list.html', {'products': products, 'q': q})


@admin_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product added.')
        return redirect('product_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': 'Add product', 'back': 'product_list'})


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('product_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': f'Edit {product.name}', 'back': 'product_list'})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        try:
            product.delete()
            messages.success(request, 'Product deleted.')
        except ProtectedError:
            # product already used in a sale/purchase: keep history, hide it instead
            product.is_active = False
            product.save(update_fields=['is_active'])
            messages.warning(request, 'Product has sales/purchase history, so it was deactivated instead of deleted.')
        return redirect('product_list')
    return render(request, 'crud/confirm_delete.html',
                  {'object': product, 'back': 'product_list'})


# ---------- Suppliers ----------

@admin_required
def supplier_list(request):
    return render(request, 'catalog/supplier_list.html',
                  {'suppliers': Supplier.objects.order_by('name')})


@admin_required
def supplier_add(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier added.')
        return redirect('supplier_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': 'Add supplier', 'back': 'supplier_list'})


@admin_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier updated.')
        return redirect('supplier_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': f'Edit {supplier.name}', 'back': 'supplier_list'})


@admin_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        try:
            supplier.delete()
            messages.success(request, 'Supplier deleted.')
        except ProtectedError:
            messages.error(request, 'This supplier has purchase records and cannot be deleted.')
        return redirect('supplier_list')
    return render(request, 'crud/confirm_delete.html',
                  {'object': supplier, 'back': 'supplier_list'})