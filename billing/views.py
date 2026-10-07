import json
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product
from .models import Sale, SaleItem, Payment, LedgerEntry


class BillError(Exception):
    pass


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@login_required
def pos(request):
    products = list(
        Product.objects.filter(is_active=True, stock__gt=0)
        .values('id', 'name', 'barcode', 'price', 'gst_percent', 'stock',
                'unit', 'size', 'color')
    )
    for p in products:
        p['price'] = float(p['price'])
        p['gst_percent'] = float(p['gst_percent'])
        p['stock'] = float(p['stock'])
        p['barcode'] = p['barcode'] or ''
    return render(request, 'billing/pos.html', {'products': products})


@login_required
@require_POST
def checkout(request):
    # 1. Read and validate what the browser sent
    try:
        cart = json.loads(request.POST.get('cart', '[]'))
        discount = money(request.POST.get('discount') or '0')
        wanted = {}
        for row in cart:
            pid = int(row['id'])
            qty = Decimal(str(row['qty'])).quantize(Decimal('0.01'))
            if qty <= 0:
                raise ValueError
            wanted[pid] = wanted.get(pid, 0) + qty
    except (ValueError, TypeError, KeyError, ArithmeticError):
        messages.error(request, 'Invalid bill data. Please try again.')
        return redirect('pos')

    method = request.POST.get('method')
    if not wanted:
        messages.error(request, 'Add at least one product.')
        return redirect('pos')
    if method not in dict(Payment.METHODS):
        messages.error(request, 'Choose a payment method.')
        return redirect('pos')
    if discount < 0:
        messages.error(request, 'Discount cannot be negative.')
        return redirect('pos')

    customer_name = request.POST.get('customer_name', '').strip()[:100]
    customer_phone = request.POST.get('customer_phone', '').strip()[:20]

    # 2. Save everything together, or nothing at all
    try:
        with transaction.atomic():
            products = {
                p.id: p for p in
                Product.objects.select_for_update().filter(id__in=wanted, is_active=True)
            }
            lines, subtotal = [], Decimal('0')
            for pid, qty in wanted.items():
                p = products.get(pid)
                if p is None:
                    raise BillError('A product in the cart is no longer available.')
                if p.unit == 'pcs' and qty != qty.to_integral_value():
                    raise BillError(f'{p.name} is sold in whole pieces.')
                if qty > p.stock:
                    raise BillError(f'Only {p.stock} of {p.name} in stock.')
                line_total = money(p.price * qty)
                lines.append((p, qty, line_total))
                subtotal += line_total
            if discount > subtotal:
                raise BillError('Discount cannot be more than the subtotal.')

            gst_total = Decimal('0')
            for p, qty, line_total in lines:
                share = discount * line_total / subtotal if subtotal else Decimal('0')
                gst_total += (line_total - share) * p.gst_percent / 100
            gst_total = money(gst_total)
            total = money(subtotal - discount + gst_total)

            sale = Sale.objects.create(
                bill_no=uuid.uuid4().hex[:20], staff=request.user,
                subtotal=subtotal, discount=discount, gst_total=gst_total, total=total,
                customer_name=customer_name, customer_phone=customer_phone,
            )
            sale.bill_no = f'INV{sale.pk:05d}'
            sale.save(update_fields=['bill_no'])

            for p, qty, line_total in lines:
                SaleItem.objects.create(
                    sale=sale, product=p, quantity=qty,
                    unit_price=p.price, gst_percent=p.gst_percent,
                )
                p.stock -= qty
                p.save(update_fields=['stock'])

            Payment.objects.create(sale=sale, method=method, amount=total)
            LedgerEntry.objects.create(
                kind='sale', amount=total, sale=sale,
                description=f'Bill {sale.bill_no}',
            )
    except BillError as e:
        messages.error(request, str(e))
        return redirect('pos')

    return redirect('receipt', pk=sale.pk)


@login_required
def receipt(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('staff').prefetch_related('items__product', 'payments'),
        pk=pk,
    )
    if not request.user.is_admin_role and sale.staff_id != request.user.id:
        raise PermissionDenied
    return render(request, 'billing/receipt.html', {'sale': sale})


@login_required
def sale_list(request):
    sales = Sale.objects.select_related('staff').order_by('-created_at')
    if not request.user.is_admin_role:
        sales = sales.filter(staff=request.user)
    q = request.GET.get('q', '').strip()
    if q:
        sales = sales.filter(
            Q(bill_no__icontains=q) | Q(customer_name__icontains=q) | Q(customer_phone__icontains=q)
        )
    return render(request, 'billing/sale_list.html', {'sales': sales[:200]})
