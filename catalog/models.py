from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    def __str__(self): return self.name

class Product(models.Model):
    UNITS = [('pcs', 'Pieces'), ('meter', 'Meters')]
    name = models.CharField(max_length=150)
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True)
    category = models.CharField(max_length=80, blank=True)
    brand = models.CharField(max_length=80, blank=True, default='')
    fabric = models.CharField(max_length=80, blank=True, default='')
    size = models.CharField(max_length=30, blank=True, default='')
    color = models.CharField(max_length=40, blank=True, default='')
    hsn_code = models.CharField('HSN code', max_length=12, blank=True, default='')
    unit = models.CharField(max_length=10, choices=UNITS, default='pcs')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    low_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    @property
    def due(self):
        return self.total - self.paid

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)