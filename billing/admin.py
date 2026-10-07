from django.contrib import admin
from .models import Sale, SaleItem, Payment, LedgerEntry

admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(Payment)
admin.site.register(LedgerEntry)