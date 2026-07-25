# SYRA Fresh — Phase 1 Stability Pass

Scope of this pass, per instructions: **audit and fix bugs in the existing
project only.** No new architecture (District/Hub/Hub Manager, Salary
module) was added — that's Phase 2.

## What was audited

Every backend module (`app.py`, `config.py`, `extensions.py`, all of
`models/`, all of `routes/`, all of `utils/`) and the frontend admin shell,
delivery-boys page, categories/reviews/settings admin pages, and the
customer notifications page — cross-checked against the actual API
responses they consume.

## Fixed

**Aadhaar / License document viewing (the main reported bug)**
- `delivery_auth_routes.py::save_upload_file()` returned a bare relative
  path like `"aadhaar/2024...jpg"` with no leading slash. The frontend used
  that directly as a link `href`, so the browser resolved it against
  whatever admin page was open (e.g. `/admin/aadhaar/...jpg`) instead of the
  real `/static/uploads/aadhaar/...jpg` location — guaranteed 404. Now
  returns the full `/static/uploads/{subfolder}/{filename}` path, matching
  how product images already worked.
- `frontend/admin/delivery-boys.html` rendered plain `<a>` text links (and
  had no button at all for the driving license). Replaced with three
  labeled buttons — **View Aadhaar Front**, **View Aadhaar Back**, **View
  Driving License** — that open in a new tab and resolve the URL through
  `resolveAdminImage()`.
- `resolveAdminImage()` was made defensive so any documents already saved
  under the old broken path format still open correctly.

**Broken/missing APIs**
- `GET /api/admin/categories` didn't exist (documented gap). The admin
  Categories page was calling the *public* `/api/categories`, which only
  returns active categories and never included `is_active`/`sort_order` —
  so deactivating a category made it disappear from the admin's own screen
  with no way to bring it back through the UI. Added the real admin
  endpoint; `serialize_category()` now also returns `is_active` and
  `sort_order`.
- `serialize_review()` didn't return `is_approved` (documented gap), so the
  admin Reviews page's approval state reset on every reload. Fixed.
- No admin-profile or change-password endpoints existed (documented gap) —
  Settings page silently only wrote to `localStorage`. Added
  `GET/PUT /api/admin/me` and `POST /api/admin/change-password`, and wired
  Settings up to them for real.
- `DELETE /api/notifications/<id>` didn't exist. The customer notifications
  page already rendered a "Delete" button that just showed a "not available
  yet" toast. Added the endpoint (same auth/ownership check as
  mark-as-read) and wired the button to it.

**Silent data bug**
- Customer notifications were created but could **never be retrieved** —
  `notify_customer()` stored `recipient_id` as whatever type was passed in
  (a plain string, since `orders_col` stores `user_id` as a string), while
  `GET /api/notifications` looked it up using the customer's real
  `ObjectId`. Mongo treats those as different values, so the query always
  came back empty. Normalized to `ObjectId` in `notification_service.py`.

**Broken UI behavior**
- `delivery-boys.html` pagination: clicking to page 2+ while on the "All"
  filter silently returned zero results, because `status=null` was
  interpolated into the `onclick` handler as the *string* `'null'`, which
  is truthy. Fixed the interpolation to pass a real `null`.
- Admin topbar showed the generic title "Admin" instead of a real page name
  on the Delivery Boys, Assignments, and Notifications pages — those three
  were missing from the `PAGE_TITLES` map in `admin.js`. Added.
- `delivery_routes.py`'s dashboard ran the exact same COD-total aggregation
  query twice (once discarded, once for real). Reduced to one call.

## Also added

- `seed.py` now also creates one pre-approved sample delivery boy account
  (`delivery@syrafresh.com` / `Delivery@123`) so the delivery panel can be
  logged into and tested immediately, without a manual register-then-admin-approve
  round trip.

## Not touched (intentionally, out of Phase 1 scope)

- Customer-facing "forgot password" is still a documented "coming soon" in
  the FAQ — no customer password-reset flow exists yet (only the delivery
  boy panel has one). This is a missing feature, not a broken one; adding
  it is a reasonable Phase 1.5/2 item if you want it before the District/Hub
  work.

## Sample accounts after running `python seed.py`

| Role | Email | Password |
|---|---|---|
| Admin | admin@syrafresh.com | Admin@12345 |
| Delivery Boy | delivery@syrafresh.com | Delivery@123 |

(No Hub Manager account yet — that role doesn't exist until Phase 2.)

---

# Phase 2 — District → Hub → Hub Manager Architecture

Adds the enterprise structure on top of the Phase 1-stabilized codebase,
without touching any of the Phase 1 fixes above. No feature described in
the architecture brief was skipped; two deliberate simplifications are
called out at the end.

## Data model

- **Districts** (`districts_col`) → **Hubs** (`hubs_col`, one district has
  many hubs) → **Hub Manager** (`hub_managers_col`, exactly one per hub,
  enforced by a unique sparse index on `hub_id`) → **Delivery Boys**
  (`delivery_boys_col.hub_id`, many per hub).
- `seed.py` seeds all 6 Phase 1 districts with their 3 hubs each (18 hubs
  total): Tenkasi, Tirunelveli, Thoothukudi, Madurai, Virudhunagar,
  Kanyakumari — exactly as specified.
- Orders now carry `hub_id`/`hub_name`, resolved automatically at checkout
  by matching the delivery address's city against a hub name. An order
  whose city doesn't match any hub simply has `hub_id: null` — still a
  valid order, just not visible to any Hub Manager (only the Super Admin
  sees every order regardless of hub).

## RBAC

- New `hub_manager_required` decorator (`utils/auth_utils.py`), same shape
  as `admin_required`/`delivery_boy_required`. Every Hub Manager route
  filters its MongoDB queries by `request.current_hub_manager["hub_id"]` -
  a Hub Manager can never query another hub's data, full stop.
- Hub Manager accounts are Super Admin-created only - no public
  self-registration (a hub can only have one manager).

## Super Admin — new capabilities

- **District Management** (`/admin/districts.html`): create/edit/
  activate-deactivate/delete districts.
- **Hub Management** (`/admin/hubs.html`): create/edit/delete hubs under a
  district; see each hub's manager and delivery boy count at a glance.
- **Hub Manager Management** (`/admin/hub-managers.html`): create accounts,
  edit name/mobile, reassign to a different hub, enable/disable, delete.
- **Delivery Boys page**: now shows each delivery boy's hub, plus a
  **Transfer** button/modal to move them to a different hub
  (`POST /api/admin/delivery-boys/<id>/transfer`) - exactly the "Transfer
  Delivery Boys" feature from the brief.
- Delivery boy registration (`frontend/delivery/register.html`) now
  requires picking a district then a hub (cascading dropdowns, backed by
  new unauthenticated `GET /api/districts` / `GET /api/hubs?district_id=`
  endpoints) - every new delivery boy is hub-assigned from day one.

## Hub Manager — new panel (`frontend/hubmanager/`)

A full second admin-style panel, visually consistent with the Super Admin
panel (same `admin.css`/design system), scoped entirely to one hub:

- **Hub Dashboard** — orders, delivery boys, revenue stats for this hub only.
- **Orders** — list this hub's orders, filter by status, **assign an order**
  to one of this hub's own approved delivery boys.
- **Delivery Boys** — view this hub's delivery boys; edit their delivery
  area / available time. (Approval, suspension, and hub transfer remain
  Super Admin-only, matching the brief's role split.)
- **Customers** — customers who've ordered from this hub.
- **Stock** — read-only view of the company-wide catalog (see
  simplification note below).
- **Attendance** — mark present/absent/half-day/leave per delivery boy per
  day, with a date picker.
- **Reports** — 30-day daily orders/revenue, breakdown by status, top
  delivery boys by completed deliveries, all scoped to this hub.
- **Settings** — profile name + change password.

## Deliberate simplifications (called out rather than hidden)

- **Stock is company-wide, not per-hub.** SYRA Fresh's existing product
  catalog has a single shared `stock` count per product, not a per-hub
  warehouse model. Splitting inventory per hub would be a schema change
  well beyond "add the District/Hub/Hub Manager architecture," so the Hub
  Manager's Stock page is intentionally read-only against the same catalog
  the Super Admin manages. Flagged clearly in the page itself.
- **Order → hub matching is by city-name match**, not a delivery radius or
  pincode-range lookup (which would need a geocoding step this project
  doesn't have). Good enough for the 18 named towns in the Phase 1 rollout;
  worth revisiting if hubs ever need to cover multiple towns/pincodes each.

## Sample Hub Manager account (from `python seed.py`)

| Role | Email | Password | Hub |
|---|---|---|---|
| Hub Manager | hubmanager@syrafresh.com | HubManager@123 | Tenkasi |

The sample delivery boy account is now also assigned to the Tenkasi hub,
so you can log in as the Hub Manager and immediately see that delivery boy
in the Delivery Boys page.

## Testing note

This sandbox has no outbound network access, so a live `pip install
pymongo` + running Flask server smoke test wasn't possible here. Every
backend file was verified with `python -m py_compile` (all pass), and
every blueprint's URL prefix was manually checked for collisions (none
found). Please run `pip install -r requirements.txt && python seed.py &&
python app.py` locally and do a quick click-through before treating this
as fully verified end-to-end.

---

# Phase 3 — Salary Module

## Data model

- **`salary_structures`** — one active pay structure per person (Hub
  Manager or Delivery Boy): monthly salary, per-order incentive rate, fuel
  allowance, and a per-day wage used for attendance deductions (defaults to
  monthly ÷ 30 if not set explicitly). One structure per person, enforced
  by a unique index on `(person_type, person_id)`.
- **`salary_transactions`** — one generated "slip" per person per month
  (unique on `(person_id, month)`), carrying its own frozen breakdown so
  editing someone's structure later never rewrites already-generated slips.

## Super Admin capabilities (all in `admin_salary_routes.py` / `/admin/salary.html`)

- **Set Salary** — monthly salary, per-order incentive, fuel allowance,
  per-day wage, separately for each Hub Manager and each Delivery Boy.
- **Generate Salary** — for one person, or in bulk for "all Delivery Boys"
  / "all Hub Managers" in a given month (optionally scoped to one hub).
  Generation computes:
  - **Per-Order Incentive** — actual delivered-order count that month ×
    the person's incentive rate (delivery boys only).
  - **Attendance-Based Salary** — reads that month's `attendance` records;
    deducts a full day's wage per "absent" day and half a day's wage per
    "half_day", using the per-day wage from their structure.
  - **Fuel Allowance** and **base Monthly Salary** flow straight from the
    structure.
  - Anyone without a structure yet, or who already has a slip for that
    month, is skipped and listed by name with the reason - never silently
    overwritten.
- **Bonus / Deduction / Fine** — `Adjust` on any still-*pending* slip
  (bonus, other deductions, a fine with an optional reason); recalculates
  gross/net immediately. Once a slip is marked **Paid it's locked** - no
  further adjustment or deletion - so paid history stays trustworthy.
- **Pay Salary button** — marks a slip Paid with a timestamp, the admin who
  paid it, and an optional payment reference.
- **Salary History** — filterable by role, month, and status, with
  pagination.
- **Generate Salary Slip** — every slip has a `View Slip` button that opens
  a print-friendly payslip (`/admin/salary-slip.html?id=...`) showing
  attendance, the full earnings/deductions breakdown, and net pay, plus a
  **Download PDF** button that generates and downloads a real PDF file
  server-side (see "Real PDF generation" below - added after this phase was
  first drafted, once it was explicitly requested).

## Hub Manager / Delivery Boy side

- Both get a **read-only "My Salary" page** listing their own slips with
  status and a `View Slip` link - they cannot set their own salary,
  generate slips, or mark themselves paid (Super Admin-only, matching the
  brief). The delivery boy panel's bottom nav and the Hub Manager sidebar
  both got a new Salary entry.
- The delivery boy's existing **Earnings** page (COD/per-delivery tracking)
  was left untouched - Salary is a distinct, separate concept (formal
  monthly payroll) and the new page links out to Earnings for clarity
  rather than merging the two.

## PDF generation (added on request, supersedes the earlier print-to-PDF note above)

Real server-side PDF generation was added using `reportlab` (pure Python,
no system dependencies - just `pip install -r requirements.txt`):
- `backend/utils/pdf_generator.py` builds a formatted salary slip PDF
  (header, employee info, attendance, itemized earnings/deductions, net
  pay, paid-status/reference) directly from a salary transaction document.
- New routes: `GET /api/admin/salary/transactions/<id>/pdf`,
  `GET /api/delivery/salary/<id>/pdf`, `GET /api/hub-manager/salary/<id>/pdf`
  - each scoped by the same auth/ownership rules as the JSON slip
  endpoints (a delivery boy or hub manager can only ever download their
  own slip).
- Every "View Slip" button across the Admin, Hub Manager, and Delivery Boy
  salary pages now sits next to a **Download PDF** button. Downloads go
  through `fetch()` + Blob (not a plain link), since the endpoint is
  authenticated and browsers can't attach an `Authorization` header to a
  normal navigation.
- Verified by actually generating a populated test PDF in this environment
  (not just compiling the code) and extracting its text back out to
  confirm every section - employee, attendance, earnings, deductions, net
  pay, paid stamp - renders in the right place with correct values.

## Sample data (from `python seed.py`)

The sample Hub Manager (₹25,000/month + ₹1,500 fuel) and sample Delivery
Boy (₹12,000/month + ₹15/order incentive + ₹1,000 fuel) both get a salary
structure seeded automatically, so `Generate Salary` has something to work
with on a fresh install without any manual setup.

---

# Phase 4 — UI Improvements

## What was already there (audited, not rebuilt)

Before touching anything, I audited `admin.css`/`theme.css` rather than
assuming a redesign was needed, since Phase 1-3 already leaned on a mature
design system: dark mode via `data-theme` + CSS variables (already
correctly wired on every Admin and Hub Manager page I built, and on the
customer storefront's shared `layout.js`), skeleton loading states,
`.empty-state` styling, toast notifications, modal open/close animations
(`@keyframes modalIn`), a shimmer loading animation, a `.fade-in` utility,
and responsive breakpoints at 1100px/900px/600px. A working CSS bar-chart
component already powered real charts on the Admin Dashboard and Sales
Reports pages. None of that needed rebuilding - it needed *auditing for
gaps and consistency*, which is what this phase actually did.

## Real bug found and fixed: dark mode broke outside Settings

The delivery boy panel's dark mode toggle (`delivery/settings.html`) wrote
to `localStorage.setItem("theme", ...)` and only applied `data-theme` on
that one page. Every other delivery page (Dashboard, Orders, History,
Earnings, Salary, Profile) never checked it and never applied it, so
turning on dark mode in Settings would silently flip back to light the
moment you navigated anywhere else. Fixed by:
- Applying the theme globally in `delivery-shared.js` (loaded by every
  delivery page) instead of only in `settings.html`.
- Switching the storage key from `"theme"` to `"syra_theme"`, matching the
  key the storefront and Admin/Hub Manager panels already use - dark mode
  is now one consistent site-wide preference instead of three separate
  ones with two different names.
- `order-details.html` had no theme handling *at all* (it didn't even
  include the shared script) - added it.
- Pre-login pages (delivery login/register/forgot-password) were left
  alone on purpose - most apps don't theme their auth screens, and forcing
  that in is more risk than value for this pass.

## Charts extended to the new Phase 2/3 pages

The Admin Dashboard/Reports pages already had a real revenue-by-day bar
chart; the Hub Manager's Reports page (built in Phase 2) didn't - it was
table-only. Added the same bar-chart component there, fed by the existing
`/api/hub-manager/reports` daily data, so a Hub Manager gets the same
"premium dashboard" feel the Super Admin already had.

## Search added where it was missing

The Delivery Boys admin page already had search from Phase 1. The Districts
(6 rows), Hubs (18 rows), and Hub Managers pages added in Phase 2 didn't -
added a client-side search box to Hubs (by hub/district name) and Hub
Managers (by name/email/hub/district). Districts stays unsearched
on purpose: 6 rows total doesn't need it, and a search box there would be
pure decoration.

## Animation polish

Added the existing `.fade-in` utility class to every list/table/stat-grid
render function across the Phase 2 and Phase 3 pages I built (Districts,
Hubs, Hub Managers, all Hub Manager panel pages, Admin Salary, Admin
Delivery Boys) - the same subtle fade-in-on-load the original Admin
Dashboard/Products pages already had, now applied consistently instead of
only on the pages that happened to be built first.

## What I deliberately did not touch

- The customer storefront (`frontend/pages/*`, `index.html`) already has
  loading/empty states on every page that actually fetches data; the 6
  pages without one (About, Contact, FAQ, Privacy, Login, Register) are
  static content or instant-validation forms with nothing to load, so
  there was nothing to add.
- No wholesale visual redesign of colors/typography/layout - the existing
  design system (forest-green theme, card-based layout, this exact bar
  chart style) was already coherent and "premium-dashboard"-looking;
  redoing it from scratch would have thrown away working, good design for
  no functional benefit and risked "breaking existing pages," which was an
  explicit constraint.

---

# Contact Management System

Replaces the Contact page's fake "shows a success message locally, sends
nothing anywhere" behavior with a real backend: submissions land in
MongoDB and are reviewed from two new Super Admin pages. No emails are
sent for either message type, exactly as scoped.

## How it routes

One public endpoint, `POST /api/contact`, always accepts
`multipart/form-data` (so an optional resume can ride along), and routes
to one of two collections based on the selected Topic:
- **Topic = "Careers / Job Application"** -> `career_applications`
  collection. Requires Position, Current Location, and a resume file in
  addition to the base fields.
- **Any other topic** -> `contact_messages` collection. Requires the base
  fields (name, email, phone, topic, message).

The frontend `contact.html` form shows/hides and toggles `required` on the
career-only fields (Position, Location, Resume) live as the Topic dropdown
changes - but the server validates independently and identically either
way, since a client-side toggle is never trusted as the actual guarantee.

## Resume upload security

- Extension whitelist enforced server-side (`pdf`, `doc`, `docx` only) -
  checked by inspecting the actual filename extension, not the
  client-reported MIME type.
- Explicit 5MB size limit, checked by seeking the real upload stream
  server-side (not trusting a client-supplied size).
- `werkzeug.secure_filename()` strips path separators and other unsafe
  characters before use - verified directly with a `"../../../etc/passwd.pdf"`
  filename, which correctly collapsed to a safe `etc_passwd.pdf` staying
  inside `static/uploads/resumes/`, not the ability to write anywhere else.
- A timestamp + random suffix is appended to every filename, and the save
  routine checks the target path doesn't already exist before writing
  (looping to regenerate if it somehow does) - verified with two uploads
  of identically-named files landing at two different, non-colliding
  paths. Never overwrites an existing file.
- Resume files are **not** served as static/public files directly - admin
  "View Resume" and "Download Resume" both go through an authenticated
  `GET /api/admin/career-applications/<id>/resume` endpoint (admin JWT
  required), fetched as a blob rather than a plain link, so a resume can't
  be pulled by anyone who merely guesses or finds its storage URL.

## Verified, not just compiled

Beyond `python -m py_compile` and the Node syntax checks run on everything
else in this project, the actual submission logic was exercised end-to-end
in this environment using Flask's test client (with a lightweight in-memory
stand-in for the one dependency, `pymongo`, that couldn't be installed
without network access): a valid general contact message, a request with
every field missing (confirming *all* errors are reported together, not
one-at-a-time), a Careers submission missing its required fields, and a
complete Careers submission with a real (fake-content) PDF resume - the
resume file was written to disk, read back, and byte-compared to the
original upload to confirm it round-trips correctly.

## Admin panel

Two new pages, following the exact same table/search/filter/pagination/
status-badge/toast/modal conventions as every other admin list page
(Delivery Boys, Hub Managers, Salary):
- **Contact Messages** (`/admin/contact-messages.html`) — search by
  name/email/phone, filter by status (New/Read/Closed), View (modal with
  full message), Mark as Read, Close, Delete.
- **Career Applications** (`/admin/career-applications.html`) — search by
  name/email/phone/position, filter by status (New/Reviewing/Shortlisted/
  Rejected/Hired), View Resume, Download Resume, View application detail +
  Update Status, Delete (the database record only - the resume file on
  disk is deliberately left alone rather than silently deleted, in case
  it's referenced elsewhere in a hiring workflow).

## What was intentionally left as-is

- Deleting a career application removes the database record but not the
  resume file from disk - see the note above. A scheduled cleanup job for
  orphaned resumes is a reasonable follow-up if disk usage ever becomes a
  concern, but wasn't asked for here and risks deleting a file still in
  use elsewhere.
- No admin bulk actions (bulk delete/status-change) were requested and
  none were added - each row action is deliberate and individual.
