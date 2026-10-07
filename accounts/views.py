from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from catalog.models import Product, Supplier
from .decorators import admin_required
from .forms import StaffCreateForm, StaffEditForm
from .mixins import AdminRequiredMixin
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

class StaffList(AdminRequiredMixin, ListView):
    model = User
    template_name = 'accounts/staff_list.html'
    context_object_name = 'staff'
    ordering = ['-is_active', 'username']


class StaffCreate(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = StaffCreateForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('staff_list')
    success_message = 'Staff account created.'
    extra_context = {'title': 'Add staff', 'back': 'staff_list'}


class StaffUpdate(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = StaffEditForm
    template_name = 'crud/form.html'
    success_url = reverse_lazy('staff_list')
    success_message = 'Staff account updated.'
    extra_context = {'title': 'Edit staff', 'back': 'staff_list'}

    def form_valid(self, form):
        if self.object.pk == self.request.user.pk and not form.cleaned_data['is_active']:
            form.add_error('is_active', 'You cannot deactivate your own account.')
            return self.form_invalid(form)
        return super().form_valid(form)