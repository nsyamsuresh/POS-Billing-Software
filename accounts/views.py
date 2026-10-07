from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product, Supplier
from .decorators import admin_required
from .forms import StaffForm
from .models import User


@login_required
def home(request):
    if request.user.is_admin_role:
        return redirect('dashboard')
    return redirect('pos')


@admin_required
def dashboard(request):
    low = Product.objects.filter(is_active=True, stock__lte=F('low_stock_level'))
    ctx = {
        'product_count': Product.objects.filter(is_active=True).count(),
        'supplier_count': Supplier.objects.count(),
        'staff_count': User.objects.filter(role=User.STAFF, is_active=True).count(),
        'low_stock': low.order_by('stock')[:10],
        'low_stock_count': low.count(),
    }
    return render(request, 'accounts/dashboard.html', ctx)


@login_required
def pos(request):
    return render(request, 'billing/pos.html')


# ---------- Staff management (admin only) ----------

@admin_required
def staff_list(request):
    users = User.objects.order_by('-is_active', 'username')
    return render(request, 'accounts/staff_list.html', {'users': users})


@admin_required
def staff_add(request):
    form = StaffForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Staff member created.')
        return redirect('staff_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': 'Add staff', 'back': 'staff_list'})


@admin_required
def staff_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = StaffForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        if user == request.user and (not form.cleaned_data['is_active']
                                     or form.cleaned_data['role'] != User.ADMIN) \
                and not user.is_superuser:
            messages.error(request, "You can't deactivate or demote your own account.")
        else:
            form.save()
            messages.success(request, 'Staff member updated.')
            return redirect('staff_list')
    return render(request, 'crud/form.html',
                  {'form': form, 'title': f'Edit {user.username}', 'back': 'staff_list'})


@admin_required
@require_POST
def staff_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You can't deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        messages.success(request, f"{user.username} is now {'active' if user.is_active else 'inactive'}.")
    return redirect('staff_list')