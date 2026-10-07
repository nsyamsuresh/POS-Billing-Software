from django.conf import settings
from django.db import models
from catalog.models import Product, Purchase
from decimal import Decimal

class Sale(models.Model):
    bill_no = models.CharField(max_length=20, unique=True)
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def returned_qty(self):
        return self.returnitem_set.aggregate(t=models.Sum('quantity'))['t'] or Decimal('0')

    def net_unit_price(self):
        """Per-unit refund: price plus GST, minus this item's share of the bill discount."""
        sale = self.sale
        if not sale.subtotal or not self.quantity:
            return Decimal('0')
        line = self.unit_price * self.quantity
        share = sale.discount * line / sale.subtotal
        gross = (line - share) * (1 + self.gst_percent / 100)
        return gross / self.quantity

class Payment(models.Model):
    METHODS = [("cash", "Cash"), ("card", "Card"), ("upi", "UPI")]
    sale = models.ForeignKey(Sale, related_name="payments", on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class SaleReturn(models.Model):
    sale = models.ForeignKey(Sale, related_name="returns", on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=200, blank=True)

class ReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, related_name="items", on_delete=models.CASCADE)
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

class LedgerEntry(models.Model):
    KINDS = [("sale", "Sale"), ("return", "Return"), ("purchase", "Purchase"),
             ("supplier_payment", "Supplier payment")]
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=20, choices=KINDS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # money in is +, money out is -
    description = models.CharField(max_length=200, blank=True)
    sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL)
    purchase = models.ForeignKey(Purchase, null=True, blank=True, on_delete=models.SET_NULL)