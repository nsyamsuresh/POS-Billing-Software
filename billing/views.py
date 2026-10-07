import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import F, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from catalog.models import Product
from .models import Sale, SaleItem, Payment, LedgerEntry
from catalog.models import Supplier, Purchase, PurchaseItem
from .models import SaleReturn, ReturnItem
from accounts.decorators import admin_required




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


# ---------------- Returns (admin only) ----------------

@admin_required
def return_list(request):
    returns = SaleReturn.objects.select_related('sale', 'created_by').order_by('-created_at')[:200]
    return render(request, 'billing/return_list.html', {'returns': returns})


@admin_required
def return_lookup(request):
    q = request.GET.get('q', '').strip()
    if q:
        sale = Sale.objects.filter(bill_no__iexact=q).first()
        if sale:
            return redirect('return_create', pk=sale.pk)
        messages.error(request, f'No bill found with number {q}.')
    return render(request, 'billing/return_lookup.html')


@admin_required
def return_create(request, pk):
    sale = get_object_or_404(Sale, pk=pk)

    def load_items(s):
        rows = list(s.items.select_related('product'))
        for i in rows:
            i.returned = i.returned_qty
            i.available = i.quantity - i.returned
        return rows

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()[:200]
        try:
            with transaction.atomic():
                locked = Sale.objects.select_for_update().get(pk=pk)
                refund, picked = Decimal('0'), []
                for i in load_items(locked):
                    raw = request.POST.get(f'qty_{i.pk}', '').strip()
                    if not raw:
                        continue
                    qty = Decimal(raw).quantize(Decimal('0.01'))
                    if qty <= 0:
                        continue
                    if qty > i.available:
                        raise BillError(f'Cannot return more than {i.available} of {i.product.name}.')
                    if i.product.unit == 'pcs' and qty != qty.to_integral_value():
                        raise BillError(f'{i.product.name} is returned in whole pieces.')
                    refund += i.net_unit_price() * qty
                    picked.append((i, qty))
                if not picked:
                    raise BillError('Enter a quantity for at least one item.')
                refund = money(refund)
                ret = SaleReturn.objects.create(
                    sale=locked, created_by=request.user, refund_amount=refund, reason=reason)
                for i, qty in picked:
                    ReturnItem.objects.create(sale_return=ret, sale_item=i, quantity=qty)
                    Product.objects.filter(pk=i.product_id).update(stock=F('stock') + qty)
                LedgerEntry.objects.create(
                    kind='return', amount=-refund, sale=locked,
                    description=f'Return on {locked.bill_no}')
        except BillError as e:
            messages.error(request, str(e))
        except ArithmeticError:
            messages.error(request, 'Enter valid quantities.')
        else:
            messages.success(request, f'Return saved. Refund: {refund}.')
            return redirect('return_list')

    return render(request, 'billing/return_form.html', {'sale': sale, 'items': load_items(sale)})


# ---------------- Supplier purchases (admin only) ----------------

@admin_required
def purchase_list(request):
    purchases = Purchase.objects.select_related('supplier').order_by('-date', '-pk')[:200]
    return render(request, 'billing/purchase_list.html', {'purchases': purchases})


@admin_required
def purchase_create(request):
    if request.method == 'POST':
        try:
            supplier = Supplier.objects.get(pk=request.POST.get('supplier'))
            paid = money(request.POST.get('paid') or '0')
            rows = []
            for pid, q, c in zip(request.POST.getlist('product'),
                                 request.POST.getlist('qty'),
                                 request.POST.getlist('cost')):
                if not pid:
                    continue
                q = Decimal(q).quantize(Decimal('0.01'))
                c = money(c)
                if q <= 0 or c < 0:
                    raise ValueError
                rows.append((int(pid), q, c))
            if not rows:
                raise BillError('Add at least one item.')
            total = money(sum(q * c for _, q, c in rows))
            if paid < 0 or paid > total:
                raise BillError('Paid amount must be between 0 and the total.')
            with transaction.atomic():
                purchase = Purchase.objects.create(supplier=supplier, total=total, paid=paid)
                for pid, q, c in rows:
                    p = Product.objects.select_for_update().get(pk=pid)
                    PurchaseItem.objects.create(purchase=purchase, product=p, quantity=q, unit_cost=c)
                    p.stock += q
                    p.cost = c
                    p.save(update_fields=['stock', 'cost'])
                if paid > 0:
                    LedgerEntry.objects.create(
                        kind='purchase', amount=-paid, purchase=purchase,
                        description=f'Purchase #{purchase.pk} from {supplier.name}')
        except BillError as e:
            messages.error(request, str(e))
        except (Supplier.DoesNotExist, Product.DoesNotExist, ValueError, ArithmeticError):
            messages.error(request, 'Please check the purchase details.')
        else:
            messages.success(request, 'Purchase saved and stock updated.')
            return redirect('purchase_list')

    return render(request, 'billing/purchase_form.html', {
        'suppliers': Supplier.objects.order_by('name'),
        'products': Product.objects.filter(is_active=True).order_by('name'),
    })


@admin_required
@require_POST
def purchase_pay(request, pk):
    try:
        amount = money(request.POST.get('amount') or '0')
        with transaction.atomic():
            purchase = Purchase.objects.select_for_update().select_related('supplier').get(pk=pk)
            due = purchase.total - purchase.paid
            if amount <= 0 or amount > due:
                raise BillError(f'Enter an amount between 0.01 and {due}.')
            purchase.paid += amount
            purchase.save(update_fields=['paid'])
            LedgerEntry.objects.create(
                kind='supplier_payment', amount=-amount, purchase=purchase,
                description=f'Payment for purchase #{purchase.pk} ({purchase.supplier.name})')
    except BillError as e:
        messages.error(request, str(e))
    except (ArithmeticError, Purchase.DoesNotExist):
        messages.error(request, 'Enter a valid amount.')
    else:
        messages.success(request, 'Payment recorded.')
    return redirect('purchase_list')


# ---------------- Ledger (admin only) ----------------

@admin_required
def ledger(request):
    entries = LedgerEntry.objects.select_related('sale', 'purchase').order_by('-created_at')
    kind = request.GET.get('kind', '')
    start = parse_date(request.GET.get('from', ''))
    end = parse_date(request.GET.get('to', ''))
    if kind in dict(LedgerEntry.KINDS):
        entries = entries.filter(kind=kind)
    if start:
        entries = entries.filter(created_at__date__gte=start)
    if end:
        entries = entries.filter(created_at__date__lte=end)
    totals = entries.aggregate(
        inflow=Sum('amount', filter=Q(amount__gt=0)),
        outflow=Sum('amount', filter=Q(amount__lt=0)),
        net=Sum('amount'),
    )
    return render(request, 'billing/ledger.html', {
        'entries': entries[:300], 'totals': totals,
        'kinds': LedgerEntry.KINDS, 'kind': kind,
        'start': request.GET.get('from', ''), 'end': request.GET.get('to', ''),
    })