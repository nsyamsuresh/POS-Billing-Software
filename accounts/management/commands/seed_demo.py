from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import User
from catalog.models import Product, Supplier


class Command(BaseCommand):
    help = 'Create demo users, suppliers and textile products (safe to run many times)'

    def handle(self, *args, **options):
        for username, role, password in [
            ('demo_admin', User.ADMIN, 'Admin@12345'),
            ('demo_staff', User.STAFF, 'Staff@12345'),
        ]:
            user, created = User.objects.get_or_create(username=username, defaults={'role': role})
            if created:
                user.set_password(password)
                user.save()

        sri, _ = Supplier.objects.get_or_create(
            name='Sri Textiles Wholesale', defaults={'phone': '9000000001', 'address': 'Kozhikode'})
        mills, _ = Supplier.objects.get_or_create(
            name='Kerala Cotton Mills', defaults={'phone': '9000000002', 'address': 'Kannur'})

        products = [
            # barcode, name, category, size, color, hsn, unit, price, cost, stock, supplier
            ('TX1001', 'Cotton Shirt', 'Shirts', 'M', 'Blue', '6205', 'pcs', '799', '520', '25', sri),
            ('TX1002', 'Cotton Shirt', 'Shirts', 'L', 'Blue', '6205', 'pcs', '799', '520', '20', sri),
            ('TX1003', 'Cotton Shirt', 'Shirts', 'M', 'White', '6205', 'pcs', '749', '490', '30', sri),
            ('TX1004', 'Kasavu Mundu', 'Traditional', '', 'Cream', '5208', 'pcs', '1200', '850', '15', mills),
            ('TX1005', 'Denim Jeans', 'Jeans', '32', 'Indigo', '6203', 'pcs', '1499', '980', '18', sri),
            ('TX2001', 'Cotton Fabric', 'Fabric', '', 'White', '5208', 'meter', '180', '120', '120', mills),
            ('TX2002', 'Silk Fabric', 'Fabric', '', 'Maroon', '5007', 'meter', '650', '450', '60', mills),
            ('TX2003', 'Linen Fabric', 'Fabric', '', 'Beige', '5309', 'meter', '320', '210', '4', mills),
        ]
        for barcode, name, category, size, color, hsn, unit, price, cost, stock, supplier in products:
            Product.objects.get_or_create(barcode=barcode, defaults={
                'name': name, 'category': category, 'size': size, 'color': color,
                'hsn_code': hsn, 'unit': unit, 'price': Decimal(price), 'cost': Decimal(cost),
                'gst_percent': Decimal('5'), 'stock': Decimal(stock),
                'low_stock_level': Decimal('5'), 'supplier': supplier,
            })
        self.stdout.write(self.style.SUCCESS('Demo data ready.'))