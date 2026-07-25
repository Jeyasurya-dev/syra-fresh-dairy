# SYRA Fresh — Enterprise Grocery Delivery Platform

Farm-fresh dairy, ice cream, healthy snacks and fruit — delivered daily
across a District → Hub → Delivery Boy network in Tamil Nadu.

Flask + MongoDB backend, vanilla HTML/CSS/JS frontend. Four integrated
systems, one codebase: **Customer Storefront**, **Super Admin Panel**,
**Hub Manager Panel**, and **Delivery Boy Panel**, all behind role-based
JWT authentication.

> Full history of what changed and why (bug fixes, architecture decisions,
> deliberate simplifications) lives in `CHANGELOG.md`. This file is the
> "what is this and how do I run it" reference.

## Roles & access control

| Role | Panel | Scope |
|---|---|---|
| **Customer** | Storefront (`/`) | Their own account, cart, orders |
| **Delivery Boy** | `/delivery/` | Their own assigned orders, attendance, salary |
| **Hub Manager** | `/hubmanager/` | Only their own hub's orders, delivery boys, customers, attendance, salary |
| **Super Admin** | `/admin/` | Everything — districts, hubs, hub managers, delivery boys, products, orders, salary, reports |

Every protected route checks the caller's role server-side (see
`utils/auth_utils.py`) — the frontend hiding a button is never the only
thing standing between a role and data that isn't theirs.

## District → Hub → Hub Manager → Delivery Boy structure

Phase 1 rollout: 6 districts, 3 hubs each (18 hubs total), one Hub Manager
per hub, many Delivery Boys per hub.

| District | Hubs |
|---|---|
| Tenkasi | Tenkasi, Sankarankovil, Alangulam |
| Tirunelveli | Tirunelveli, Palayamkottai, Valliyur |
| Thoothukudi | Thoothukudi, Kovilpatti, Tiruchendur |
| Madurai | Madurai, Thirumangalam, Melur |
| Virudhunagar | Virudhunagar, Sivakasi, Rajapalayam |
| Kanyakumari | Nagercoil, Marthandam, Kuzhithurai |

Orders are automatically routed to a hub by matching the delivery
address's city against a hub name at checkout.

## Folder structure

```
syra-fresh/
├── backend/
│   ├── app.py                       # Flask entrypoint, all blueprint registrations
│   ├── config.py                    # Env-based configuration
│   ├── extensions.py                # MongoDB connection + all collections, password hashing, indexes
│   ├── seed.py                      # Seeds categories, products, districts/hubs, and one sample
│   │                                 # account per role (admin, hub manager, delivery boy)
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   ├── user.py  product.py  category.py  order.py  review.py       # Core storefront
│   │   ├── delivery_boy.py                                             # Delivery boy + assignments
│   │   ├── district.py  hub.py  hub_manager.py                        # District/Hub architecture
│   │   ├── salary.py                                                   # Salary structures + slips
│   │   └── contact.py                                                  # Contact messages + career applications
│   ├── routes/
│   │   ├── auth_routes.py, product_routes.py, cart_routes.py,
│   │   │   order_routes.py, review_routes.py                          # Customer-facing API
│   │   ├── admin_routes.py                                             # Admin auth/dashboard/catalog/
│   │   │                                                                #   orders/customers/profile
│   │   ├── delivery_auth_routes.py, delivery_routes.py,
│   │   │   admin_delivery_routes.py                                    # Delivery boy system
│   │   ├── admin_district_routes.py, admin_hub_routes.py,
│   │   │   admin_hub_manager_routes.py, hub_manager_auth_routes.py,
│   │   │   hub_manager_routes.py, public_hub_routes.py                 # District/Hub architecture
│   │   ├── admin_salary_routes.py                                      # Salary Module (admin side)
│   │   ├── contact_routes.py, admin_contact_routes.py                  # Contact Management System
│   │   └── notifications_routes.py
│   └── utils/
│       ├── auth_utils.py            # JWT issue/verify + admin_required, delivery_boy_required,
│       │                             #   hub_manager_required decorators
│       ├── validators.py            # Form/field validation
│       ├── notification_service.py  # In-app notification creation/delivery
│       └── pdf_generator.py         # Server-side salary slip PDF generation (reportlab)
│
└── frontend/                        # Static site — served with `frontend/` as the web root
    ├── index.html, css/, js/, pages/    # Customer storefront (18 pages)
    ├── admin/                           # Super Admin panel
    │   ├── dashboard.html, products.html, categories.html, inventory.html,
    │   │   orders.html, assignments.html, customers.html, coupons.html,
    │   │   reviews.html, reports.html, notifications.html, settings.html
    │   ├── districts.html, hubs.html, hub-managers.html                # District/Hub management
    │   ├── delivery-boys.html                                          # incl. hub transfer
    │   ├── salary.html, salary-slip.html                               # Salary Module
    │   ├── contact-messages.html, career-applications.html            # Contact Management System
    │   └── css/admin.css, js/admin-api.js, js/admin.js
    ├── delivery/                         # Delivery Boy panel
    │   ├── login.html, register.html (district/hub selection), dashboard.html,
    │   │   assignments.html, order-details.html, history.html, earnings.html,
    │   │   salary.html, profile.html, settings.html, forgot-password*.html
    │   └── delivery-shared.js
    └── hubmanager/                       # Hub Manager panel
        ├── login.html, dashboard.html, orders.html, delivery-boys.html,
        │   customers.html, inventory.html, attendance.html, reports.html,
        │   salary.html, settings.html
        └── js/hubmanager-api.js, js/hubmanager.js
```

## Getting started (backend)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in your Mongo URI, JWT secret, Razorpay test keys
python seed.py               # seeds categories, products, districts/hubs, and one sample
                              # account per role - see table below
python app.py                 # runs on http://localhost:5000
```

## Getting started (frontend)

The frontend is static — serve it with any static server, e.g.:

```bash
cd frontend
python -m http.server 5500
```

Then open:
- `http://localhost:5500` — customer storefront
- `http://localhost:5500/admin/login.html` — Super Admin panel
- `http://localhost:5500/hubmanager/login.html` — Hub Manager panel
- `http://localhost:5500/delivery/login.html` — Delivery Boy panel

If your API runs somewhere other than `http://localhost:5000/api`, set it
before the other scripts load:

```html
<script>window.SYRA_API_BASE = 'https://your-api.example.com/api';</script>
```

## Sample accounts (from `python seed.py`)

| Role | Email | Password | Scope |
|---|---|---|---|
| Super Admin | admin@example.com | xxxxxxxxxx | Everything |
| Hub Manager | hubmanager@syrafresh.com | HubManager@123 | Tenkasi hub |
| Delivery Boy | delivery@syrafresh.com | Delivery@123 | Tenkasi hub |

Change these immediately in a real deployment. Both the Hub Manager and
Delivery Boy sample accounts also get a starter salary structure seeded,
so **Generate Salary** has real data to work with immediately.

## What's built and working

**Customer Storefront (complete):** full catalog with search/filter/sort/
pagination, cart & wishlist, Razorpay + COD checkout, order history &
tracking, reviews, notifications — 18 pages, dark/light mode, responsive.

**Super Admin Panel (complete):** dashboard with charts, product/category/
inventory/coupon/review management, order management with delivery
assignment, customer management, District/Hub/Hub Manager management,
delivery boy management with hub transfer, the full Salary Module (set
salary, generate slips, bonus/deduction/fine adjustments, Pay Salary,
downloadable PDF slips), Contact Messages and Career Applications
management (with resume view/download), sales reports with CSV export,
notifications, and account settings.

**Hub Manager Panel (complete):** dashboard, orders (view + assign to own
hub's delivery boys), delivery boys (view/edit within hub), customers,
read-only company-wide stock view, attendance marking, hub-scoped reports
with charts, own salary history with PDF download, and account settings.
Every query is scoped server-side to the manager's own hub.

**Delivery Boy Panel (complete):** dashboard, assigned orders with OTP
delivery verification, order history, COD earnings tracking, salary
history with PDF slip downloads, profile (with working Aadhaar Front/Back
and Driving License document viewing), and settings including a dark mode
toggle that now actually applies across every page.

**Backend (complete):** full REST API for all four systems above, RBAC
enforced via per-role JWT decorators, MongoDB indexes (including uniqueness
constraints like "one Hub Manager per hub"), input validation, secure file
uploads served through a dedicated static route, and server-side PDF
generation for salary slips.

See `CHANGELOG.md` for the complete phase-by-phase record of bug fixes,
architecture additions, and the handful of deliberate scope decisions
(e.g. stock stays company-wide rather than per-hub) made along the way.
