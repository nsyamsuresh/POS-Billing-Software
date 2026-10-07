from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .decorators import admin_required

@login_required
def home(request):
    if request.user.is_admin_role:
        return redirect('dashboard')
    return redirect('pos')

@admin_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

@login_required
def pos(request):
    return render(request, 'billing/pos.html')