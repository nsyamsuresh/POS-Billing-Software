from django import forms
from accounts.forms import BootstrapMixin
from .models import Supplier, Product

class SupplierForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'barcode', 'category', 'brand', 'fabric', 'size', 'color',
                  'hsn_code', 'unit', 'price', 'cost', 'gst_percent',
                  'stock', 'low_stock_level', 'supplier', 'is_active']