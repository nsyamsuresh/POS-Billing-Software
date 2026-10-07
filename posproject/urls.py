from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views as acc
from catalog import views as cat

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', acc.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', acc.dashboard, name='dashboard'),
    path('billing/', acc.pos, name='pos'),

    path('staff/', acc.StaffList.as_view(), name='staff_list'),
    path('staff/add/', acc.StaffCreate.as_view(), name='staff_add'),
    path('staff/<int:pk>/edit/', acc.StaffUpdate.as_view(), name='staff_edit'),

    path('suppliers/', cat.SupplierList.as_view(), name='supplier_list'),
    path('suppliers/add/', cat.SupplierCreate.as_view(), name='supplier_add'),
    path('suppliers/<int:pk>/edit/', cat.SupplierUpdate.as_view(), name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', cat.SupplierDelete.as_view(), name='supplier_delete'),

    path('products/', cat.ProductList.as_view(), name='product_list'),
    path('products/add/', cat.ProductCreate.as_view(), name='product_add'),
    path('products/<int:pk>/edit/', cat.ProductUpdate.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', cat.ProductDelete.as_view(), name='product_delete'),
]