# SYRA Fresh - Production-Ready Multi-Role E-Commerce Platform

> **Note:** this document describes the original three-role system (Customer,
> Delivery Boy, Admin) as first built. The platform has since grown a fourth
> role (**Hub Manager**) plus a District → Hub architecture and a full
> Salary Module — see `README.md` for the current, accurate architecture
> and `CHANGELOG.md` for the complete history of what was added and why.
> The delivery/notification/tracking details below are still accurate.

## 🎯 Overview

SYRA Fresh is a **production-ready, multi-role e-commerce platform** built with Flask and MongoDB, featuring:
- Customer e-commerce portal with shopping, orders, and tracking
- Admin panel for inventory, orders, and delivery management  
- **Delivery Boy Portal** with real-time order assignments and tracking
- **Advanced Notification System** (Email, SMS, WhatsApp, In-App)
- **Live Order Tracking** with GPS integration ready
- **Role-Based Authentication** with JWT
- Scalable architecture for rapid deployment

## 📋 Architecture

### Three-Role System

```
┌─────────────────────────────────────────────────────────────┐
│                    SYRA Fresh Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
├─ CUSTOMER ROLE (Customer Portal)                             │
│  ├─ Register & Login                                         │
│  ├─ Browse Products & Shop                                   │
│  ├─ Manage Cart & Wishlist                                   │
│  ├─ Checkout with COD/Razorpay                               │
│  ├─ Track Orders (Live Status)                               │
│  ├─ View Delivery Boy Details                                │
│  ├─ Manage Addresses                                         │
│  └─ Order History & Reviews                                  │
│                                                               │
├─ DELIVERY BOY ROLE (Delivery Portal)                         │
│  ├─ Register with Aadhar/License Verification               │
│  ├─ Admin Approval Required                                  │
│  ├─ Login (Approved Only)                                    │
│  ├─ View Assigned Orders (Dashboard)                         │
│  ├─ Update Delivery Status                                   │
│  ├─ Real-Time Location Updates                               │
│  ├─ COD Collection & Submission                              │
│  ├─ Performance Analytics                                    │
│  ├─ Earnings Tracking                                        │
│  └─ Online/Offline Status Toggle                             │
│                                                               │
├─ ADMIN ROLE (Admin Panel)                                    │
│  ├─ Delivery Boy Management                                  │
│  │  ├─ View All Applications                                 │
│  │  ├─ Approve/Reject Registrations                          │
│  │  ├─ Verify Documents                                      │
│  │  ├─ Suspend/Activate Accounts                             │
│  │  └─ Assign Orders to Delivery Boys                        │
│  ├─ Order Management                                         │
│  │  ├─ View All Orders                                       │
│  │  ├─ Track Delivery Status                                 │
│  │  └─ Manage Returns/Refunds                                │
│  ├─ Inventory Management                                     │
│  ├─ Customer Management                                      │
│  ├─ Reports & Analytics                                      │
│  └─ Notification Management                                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Database Collections

```
MongoDB
├─ users (Customer accounts)
├─ admins (Admin accounts)
├─ delivery_boys (Delivery partner profiles)
├─ products (Product catalog)
├─ categories (Product categories)
├─ orders (Customer orders)
├─ carts (Shopping carts)
├─ wishlists (Saved items)
├─ reviews (Product reviews)
├─ coupons (Discount codes)
├─ banners (Promotional banners)
├─ addresses (User addresses)
├─ delivery_assignments (Order assignments to delivery boys)
├─ delivery_locations (GPS tracking history)
├─ notifications (Notification queue)
└─ notification_logs (Delivery attempt logs)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB 4.0+
- Node.js (optional, for frontend build tools)

### Installation

1. **Clone & Setup Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Configure MongoDB, JWT, and other settings
python app.py
```

2. **Setup Frontend**
```bash
# No build step required - pure HTML/CSS/JS
# Serve frontend directory via any HTTP server
python -m http.server 8080 --directory frontend/
```

3. **Access the Application**
- **Customer Portal**: http://localhost:8080
- **Admin Panel**: http://localhost:8080/admin
- **Delivery Portal**: http://localhost:8080/delivery
- **API**: http://localhost:5000/api

## 📁 Project Structure

```
syra-fresh/
├── backend/
│   ├── app.py                          # Flask app entry point
│   ├── config.py                       # Configuration settings
│   ├── extensions.py                   # DB & utilities
│   ├── seed.py                         # Sample data
│   ├── requirements.txt                # Python dependencies
│   ├── models/
│   │   ├── user.py                     # Customer schema
│   │   ├── delivery_boy.py            # Delivery partner schema
│   │   ├── order.py                    # Order schema
│   │   ├── product.py                  # Product schema
│   │   ├── category.py                 # Category schema
│   │   └── review.py                   # Review schema
│   ├── routes/
│   │   ├── auth_routes.py              # Customer auth
│   │   ├── delivery_auth_routes.py     # Delivery boy auth
│   │   ├── delivery_routes.py          # Delivery operations
│   │   ├── admin_routes.py             # Admin operations
│   │   ├── admin_delivery_routes.py    # Admin delivery mgmt
│   │   ├── product_routes.py           # Product catalog
│   │   ├── order_routes.py             # Order management
│   │   ├── cart_routes.py              # Shopping cart
│   │   ├── review_routes.py            # Reviews
│   │   └── notifications_routes.py     # Notifications
│   └── utils/
│       ├── auth_utils.py               # JWT & decorators
│       ├── validators.py               # Input validation
│       └── notification_service.py     # Notification system
│
├── frontend/
│   ├── index.html                      # Customer homepage
│   ├── js/
│   │   ├── api.js                      # API client
│   │   ├── auth.js                     # Auth logic
│   │   ├── cart.js                     # Cart logic
│   │   └── main.js                     # Core functionality
│   ├── css/
│   │   ├── style.css                   # Main styles
│   │   ├── theme.css                   # Dark/light theme
│   │   └── pages.css                   # Page-specific styles
│   ├── pages/
│   │   ├── login.html                  # Customer login
│   │   ├── register.html               # Customer registration
│   │   ├── shop.html                   # Product listing
│   │   ├── cart.html                   # Shopping cart
│   │   ├── checkout.html               # Checkout
│   │   ├── track-order.html            # Order tracking
│   │   ├── orders.html                 # Order history
│   │   ├── profile.html                # User profile
│   │   └── ...other pages
│   ├── admin/
│   │   ├── dashboard.html              # Admin dashboard
│   │   ├── products.html               # Product management
│   │   ├── orders.html                 # Order management
│   │   ├── customers.html              # Customer management
│   │   ├── delivery-boys.html          # Delivery boy mgmt
│   │   └── ...other admin pages
│   └── delivery/
│       ├── login.html                  # Delivery boy login
│       ├── register.html               # Delivery boy registration
│       ├── dashboard.html              # Delivery dashboard
│       ├── assignments.html            # View assignments
│       ├── order-details.html          # Order details
│       ├── history.html                # Delivery history
│       └── profile.html                # Delivery profile
│
└── README.md
```

## 🔐 Authentication & Authorization

### JWT-Based Multi-Role System

**Role-Based Decorators:**
```python
@login_required          # Customer routes
@delivery_boy_required   # Delivery boy routes
@admin_required          # Admin routes
```

**Token Payload:**
```json
{
  "sub": "user_id",
  "role": "customer|delivery_boy|admin",
  "iat": 1234567890,
  "exp": 1234567890
}
```

### Secure Endpoints

- **Customer**: `/api/auth/`, `/api/orders/`, `/api/cart/`
- **Delivery Boy**: `/api/delivery/auth/`, `/api/delivery/assignments/`
- **Admin**: `/api/admin/*`

## 📦 Delivery Boy Module

### Registration Flow

1. **Delivery boy fills registration form** with documents
   - Personal details (Name, Email, Mobile)
   - Address information
   - Aadhar & License documents (Photo upload)
   - Vehicle details
   - Operational preferences

2. **Documents uploaded to:**
   ```
   uploads/
   ├─ aadhaar/      # Aadhar photos
   ├─ license/      # License photos
   └─ profile/      # Profile photos
   ```

3. **Admin verifies registration:**
   - Review documents
   - Approve/Reject
   - Status becomes accessible for login

### Delivery Workflow

```
Order Assigned → Delivery Boy Notified
    ↓
Pick Up Order → Update Status to "Picked Up"
    ↓
Out For Delivery → Update Location, Notify Customer
    ↓
Deliver → Mark as Delivered, Update COD
    ↓
Complete → Performance metrics updated
```

### Key APIs

**Authentication:**
- `POST /api/delivery/auth/register` - Registration
- `POST /api/delivery/auth/login` - Login
- `GET /api/delivery/auth/me` - Current profile
- `PUT /api/delivery/auth/me` - Update profile

**Operations:**
- `GET /api/delivery/dashboard` - Dashboard stats
- `GET /api/delivery/assignments` - Assigned orders
- `GET /api/delivery/assignments/<id>` - Order details
- `PUT /api/delivery/assignments/<id>/status` - Update status
- `POST /api/delivery/assignments/<id>/location` - GPS update
- `GET /api/delivery/history` - Delivery history
- `POST /api/delivery/toggle-online` - Online status

**Admin Management:**
- `GET /api/admin/delivery-boys` - List all
- `GET /api/admin/delivery-boys/<id>` - View details
- `POST /api/admin/delivery-boys/<id>/approve` - Approve
- `POST /api/admin/delivery-boys/<id>/reject` - Reject
- `POST /api/admin/delivery-boys/<id>/suspend` - Suspend
- `POST /api/admin/delivery-boys/<id>/assign-order` - Assign order

## 🔔 Notification System

### Multi-Channel Support

1. **Email** (SendGrid, AWS SES, SMTP)
2. **SMS** (Twilio, Fast2SMS, Textlocal)
3. **WhatsApp** (Meta Cloud API)
4. **In-App** (Real-time)

### Notification Types

**Customer:**
- Order Placed
- Order Packed
- Order Shipped
- Out For Delivery
- Order Delivered
- Order Cancelled
- Refund Processed
- Delivery Boy Assigned

**Delivery Boy:**
- New Assignment
- Assignment Cancelled
- Reminder Notifications

**Admin:**
- New Delivery Boy Registration
- New Order
- Failed Delivery

### Implementation (Extensible)

```python
# Send notification to customer
NotificationService.notify_customer(
    customer_id,
    "order_placed",
    {"order_number": "SYRA123456"},
    channels=["in_app", "email", "sms"]
)

# Send to delivery boy
NotificationService.notify_delivery_boy(
    delivery_boy_id,
    "delivery_new_assignment",
    {"order_number": "SYRA123456"}
)
```

## 📍 Live Order Tracking

### GPS Integration Architecture

1. **Delivery Boy App Updates Location**
   ```
   POST /api/delivery/assignments/<id>/location
   { "latitude": 40.7128, "longitude": -74.0060 }
   ```

2. **Location Stored in `delivery_locations` Collection**
   - Timestamp for history
   - Indexed by assignment_id

3. **Customer Sees Live Marker**
   - Order tracking page fetches latest location
   - Google Maps integration ready
   - Distance & ETA calculation

### Future Enhancements

- Real-time WebSocket updates
- Estimated arrival time calculation
- Route optimization
- Heat maps for delivery density

## 🗂️ File Upload & Storage

**Upload Folder Structure:**
```
uploads/
├─ aadhaar/
│  └─ 20240718120530_front.jpg
├─ license/
│  └─ 20240718120530_license.jpg
├─ profile/
│  └─ 20240718120530_photo.jpg
└─ products/
   └─ [Product images]
```

**Security:**
- File type validation (jpg, png, pdf)
- Filename sanitization
- Size limits enforced
- Stored outside root directory

## 🛡️ Security Features

1. **Password Hashing** - Werkzeug security
2. **JWT Tokens** - HS256 algorithm
3. **CORS Protection** - Origin validation
4. **Input Validation** - All fields validated
5. **SQL/NoSQL Injection Prevention** - Parameterized queries
6. **File Upload Validation** - Type & size checks
7. **Rate Limiting Ready** - Architecture supports it

## 📊 Database Indexes

```python
# Optimized for production
users: email (unique), phone (unique)
admins: email (unique)
delivery_boys: email, mobile, status, delivery_area
products: name/description (text), category, slug
orders: user_id, order_number, delivery_boy_id
delivery_assignments: order_id, delivery_boy_id, status
notifications: recipient_id, created_at
```

## 🚀 Deployment

### Production Checklist

```
Backend:
- [ ] Set FLASK_ENV=production
- [ ] Use strong JWT_SECRET_KEY
- [ ] Configure MongoDB Atlas/Self-hosted
- [ ] Setup email service (SendGrid/SES)
- [ ] Configure SMS provider credentials
- [ ] Enable HTTPS/SSL
- [ ] Setup CORS for frontend domain
- [ ] Use Gunicorn with multiple workers
- [ ] Configure reverse proxy (Nginx)
- [ ] Enable database backups
- [ ] Setup monitoring & logging

Frontend:
- [ ] Configure API_URL for production
- [ ] Enable dark/light mode defaults
- [ ] Test all browsers
- [ ] Optimize images
- [ ] Cache busting for CSS/JS
- [ ] Setup CDN for static files
```

### Docker Deployment (Ready)

```dockerfile
# Backend
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

# Frontend (Nginx)
FROM nginx:alpine
COPY frontend/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
```

## 📈 Scalability

**Horizontal Scaling:**
- Stateless Flask backend
- MongoDB sharding ready
- Session management via JWT
- Async task queues (Celery ready)

**Caching:**
- Redis ready for sessions
- API response caching
- Database query optimization

## 🔄 API Response Format

All APIs follow standardized response:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "pagination": { "page": 1, "limit": 10, "total": 100 }
}
```

## 🐛 Error Handling

- Custom error messages
- Proper HTTP status codes
- Detailed validation errors
- Server error logging

## 📚 API Documentation

Comprehensive API endpoints with request/response examples available in `routes/` documentation.

## 🎨 UI/UX Features

- **Dark/Light Theme** - Toggle in settings
- **Responsive Design** - Mobile-first approach
- **Accessibility** - WCAG compliant
- **Loading States** - Skeleton loaders
- **Error Messages** - Clear & actionable
- **Notifications** - Toast messages

## 🔮 Future Roadmap

- [ ] Live GPS tracking map
- [ ] Video delivery verification
- [ ] Return management module
- [ ] Advanced analytics dashboard
- [ ] Payment gateway integration
- [ ] Subscription/bulk order handling
- [ ] Multi-language support
- [ ] AI-based delivery optimization
- [ ] Customer rating & review system
- [ ] Performance incentive system

## 📞 Support & Maintenance

### Monitoring
- API health checks
- Database connection monitoring
- File storage monitoring
- Notification delivery tracking

### Backup Strategy
- Daily MongoDB backups
- File upload backups
- Configuration versioning

## 📄 License

Proprietary - SYRA Fresh Platform

## 👨‍💻 Development

### Adding New Features

1. Create model in `models/`
2. Create routes in `routes/`
3. Add validation in `utils/validators.py`
4. Create frontend pages
5. Add API integration in frontend JS
6. Update documentation

### Code Standards

- PEP 8 for Python
- ES6+ for JavaScript
- Clear variable naming
- Inline comments for complex logic
- Docstrings for functions

## ✅ Testing

```bash
# Backend tests
pytest tests/

# Frontend manual testing
- Test across browsers
- Test responsive design
- Test dark/light modes
```

---

**Built with ❤️ for production-ready e-commerce**

Version: 2.0 (Multi-Role with Delivery)
Last Updated: July 2024
