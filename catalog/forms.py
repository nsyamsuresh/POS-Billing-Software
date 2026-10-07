from accounts.forms import BootstrapMixin
from django import forms
from .models import Product, Supplier


class SupplierForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'barcode', 'category', 'price', 'cost', 'gst_percent',
                  'stock', 'low_stock_level', 'supplier', 'is_active']

    def clean_barcode(self):
        # empty barcode must be saved as NULL so the unique constraint allows many blanks
        return self.cleaned_data.get('barcode') or None