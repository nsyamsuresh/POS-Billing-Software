# POS Billing Software

A point-of-sale and billing system for a textile and retail shop, built with Django and PostgreSQL. It has an Admin Portal for managing the business, a Billing Portal for staff at the counter, and a mobile-style layout that gives the complete Admin Portal on a phone-sized screen.

## Demo logins

| Role | Username | Password |
|---|---|---|
| Admin | `demo_admin` | `Admin@12345` |
| Staff | `demo_staff` | `Staff@12345` |

These accounts and the sample textile products are created by the `seed_demo` command. They exist only for testing this task.

## What it does

The **Admin Portal** covers product management (name, barcode, category, brand, fabric, size, colour, HSN code, unit, price, cost, GST rate, stock and a low-stock level), supplier management, staff management with roles and activate or deactivate, supplier purchases that add stock and track what is still owed, product returns that restock items and record the refund, a ledger of all money in and out with date and type filters, and reports (daily sales, sales by staff, top products, supplier balances, low stock). A dashboard shows the main counts and low-stock items.

The **Billing Portal** lets staff search products by name or scan a barcode, build a cart, apply a discount, take payment by cash, card or UPI, and print the bill. Cash payments show the change to return. Staff can see only their own bills, while admins can see all of them.

The **Mobile Admin UI** is the same application served under `/m/`. Every admin page and action works there, with a top bar, bottom tabs, a "More" menu and tables that turn into cards on a narrow screen.

Textile needs are handled directly: fabric can be sold by the meter in decimal quantities (for example 2.5 m) while garments are sold in whole pieces, and each size and colour is its own product with its own barcode and stock.

## Technology

The backend is Django 6 with server-rendered templates. The database is PostgreSQL on Render (SQLite locally). The frontend uses Bootstrap 5 and plain JavaScript for the billing cart. Gunicorn and WhiteNoise serve the app in production, and it is deployed on Render.

## Access control

Users have a role of Admin or Staff. Admin-only pages (products, suppliers, staff, purchases, returns, ledger, reports) are protected on the server, so a staff user who opens one of those URLs gets a 403 page. Staff land on the billing screen after login. Staff accounts are deactivated rather than deleted, so past bills keep their history, and an admin cannot deactivate their own account.

## Billing and data integrity

A sale is saved inside one database transaction. The product rows are locked, stock is checked, the bill, its items, the payment and the ledger entry are created, and stock is reduced. If anything fails, nothing is saved. Prices, GST and totals are always recalculated on the server from the database, so values sent from the browser are never trusted. A product that has been sold cannot be deleted, and should be marked inactive instead.

## Assumptions

Product prices are entered before GST. A bill discount is a flat amount on the whole bill, and GST is calculated on the discounted value of each item. A return refunds the item price plus GST, minus its share of the bill discount, and puts the stock back. A purchase from a supplier adds stock and updates the product's cost price, and it can be paid in full, in part, or later. GST rates in the demo data are sample values only.

## Known limitations

Each bill has a single payment method, and split payments are not supported. Size and colour variants are separate product records rather than one product with variants. The product search in the billing screen loads the active product list into the page, which suits a shop-sized catalogue but would need a server search for a very large one. Receipts show a single GST total rather than a CGST and SGST split. The shop name on the receipt is a placeholder in `templates/billing/receipt.html`.

## Running it locally

```
git clone https://github.com/nsyamsuresh/POS-Billing-Software.git
cd POS-Billing-Software
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the desktop layout and http://127.0.0.1:8000/m/ for the mobile layout. Without a `DATABASE_URL` setting the app uses a local SQLite file.

## Environment variables for deployment

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `False` in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `PYTHON_VERSION` | Python version for Render, for example `3.13.5` |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` | Create the first superuser during the build |

Build command on Render:

```
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && (python manage.py createsuperuser --noinput || true)
```

Start command:

```
gunicorn posproject.wsgi:application
```

## Project structure

`accounts` holds the custom user model, roles, staff management and the dashboard. `catalog` holds products, suppliers and purchase models and their pages. `billing` holds sales, payments, returns, the ledger and the printable bill. `reports` holds the reports page. `templates/` contains the shared layouts, including the desktop and mobile versions in `base.html`, and `posproject/middleware.py` serves the whole site under `/m/` with the mobile layout.



## License

Released under the MIT License. See the LICENSE file for details.
