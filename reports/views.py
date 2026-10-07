from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.decorators import admin_required
from billing.models import Sale, SaleItem, SaleReturn
from catalog.models import Product, Supplier


@admin_required
def reports(request):
    today = timezone.localdate()
    start = parse_date(request.GET.get('from', '')) or today - timedelta(days=29)
    end = parse_date(request.GET.get('to', '')) or today
    span = (start, end)

    sales = Sale.objects.filter(created_at__date__range=span)
    summary = sales.aggregate(
        bills=Count('id'), subtotal=Sum('subtotal'), discount=Sum('discount'),
        gst=Sum('gst_total'), total=Sum('total'))
    refunds = SaleReturn.objects.filter(created_at__date__range=span) \
        .aggregate(t=Sum('refund_amount'))['t'] or Decimal('0')
    net = (summary['total'] or Decimal('0')) - refunds

    daily = (sales.annotate(day=TruncDate('created_at')).values('day')
             .annotate(bills=Count('id'), total=Sum('total')).order_by('-day'))
    by_staff = (sales.values('staff__username')
                .annotate(bills=Count('id'), total=Sum('total')).order_by('-total'))

    line = ExpressionWrapper(F('unit_price') * F('quantity'),
                             output_field=DecimalField(max_digits=14, decimal_places=2))
    top_products = (SaleItem.objects.filter(sale__created_at__date__range=span)
                    .values('product__name', 'product__size', 'product__color', 'product__unit')
                    .annotate(qty=Sum('quantity'), revenue=Sum(line)).order_by('-revenue')[:10])

    supplier_dues = (Supplier.objects
                     .annotate(total=Sum('purchase__total'), paid=Sum('purchase__paid'))
                     .annotate(due=F('total') - F('paid')).filter(due__gt=0).order_by('-due'))
    low_stock = Product.objects.filter(
        is_active=True, stock__lte=F('low_stock_level')).order_by('stock')[:20]

    return render(request, 'reports/reports.html', {
        'start': start, 'end': end, 'summary': summary, 'refunds': refunds, 'net': net,
        'daily': daily, 'by_staff': by_staff, 'top_products': top_products,
        'supplier_dues': supplier_dues, 'low_stock': low_stock,
    })