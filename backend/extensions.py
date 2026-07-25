"""
SYRA Fresh - Extensions
Central place for shared instances (DB client, password hasher) so
route/model modules can import without circular imports.
"""
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

_client = MongoClient(Config.MONGO_URI)
db = _client[Config.DB_NAME]

# Collections (created lazily by MongoDB on first insert)
users_col = db["users"]
admins_col = db["admins"]
products_col = db["products"]
categories_col = db["categories"]
orders_col = db["orders"]
carts_col = db["carts"]
wishlists_col = db["wishlists"]
reviews_col = db["reviews"]
coupons_col = db["coupons"]
banners_col = db["banners"]
addresses_col = db["addresses"]

# Delivery Boy Collections
delivery_boys_col = db["delivery_boys"]
delivery_assignments_col = db["delivery_assignments"]
delivery_locations_col = db["delivery_locations"]

# Phase 2: District / Hub / Hub Manager Collections
districts_col = db["districts"]
hubs_col = db["hubs"]
hub_managers_col = db["hub_managers"]
attendance_col = db["attendance"]

# Phase 3: Salary Module
salary_structures_col = db["salary_structures"]
salary_transactions_col = db["salary_transactions"]

# Contact Management System
contact_messages_col = db["contact_messages"]
career_applications_col = db["career_applications"]

# Notifications
notifications_col = db["notifications"]
notification_logs_col = db["notification_logs"]


def ensure_indexes():
    """Create indexes used across the app. Call once on startup."""
    users_col.create_index("email", unique=True)
    users_col.create_index("phone", unique=True, sparse=True)
    admins_col.create_index("email", unique=True)
    products_col.create_index([("name", "text"), ("description", "text"), ("tags", "text")])
    products_col.create_index("category")
    products_col.create_index("slug", unique=True)
    orders_col.create_index("user_id")
    orders_col.create_index("order_number", unique=True)
    orders_col.create_index("delivery_boy_id", sparse=True)
    reviews_col.create_index([("product_id", 1), ("user_id", 1)], unique=True)
    coupons_col.create_index("code", unique=True)
    
    # Delivery Boy Indexes
    delivery_boys_col.create_index("email", unique=True)
    delivery_boys_col.create_index("mobile", unique=True)
    delivery_boys_col.create_index("aadhar_number", unique=True, sparse=True)
    delivery_boys_col.create_index("status")
    delivery_boys_col.create_index("delivery_area")
    
    # Delivery Assignment Indexes
    delivery_assignments_col.create_index("order_id", unique=True)
    delivery_assignments_col.create_index("delivery_boy_id")
    delivery_assignments_col.create_index("status")
    delivery_assignments_col.create_index("assigned_at")

    # Phase 2: District / Hub / Hub Manager Indexes
    districts_col.create_index("slug", unique=True)
    hubs_col.create_index("slug", unique=True)
    hubs_col.create_index("district_id")
    hub_managers_col.create_index("email", unique=True)
    hub_managers_col.create_index("mobile", unique=True, sparse=True)
    hub_managers_col.create_index("hub_id", unique=True, sparse=True)  # one manager per hub
    delivery_boys_col.create_index("hub_id", sparse=True)
    attendance_col.create_index([("person_id", 1), ("date", 1)], unique=True)
    attendance_col.create_index("hub_id")

    # Phase 3: Salary Indexes
    salary_structures_col.create_index([("person_type", 1), ("person_id", 1)], unique=True)
    salary_transactions_col.create_index([("person_id", 1), ("month", 1)], unique=True)
    salary_transactions_col.create_index("status")
    salary_transactions_col.create_index("person_type")
    salary_transactions_col.create_index("hub_id")

    # Contact Management System Indexes
    contact_messages_col.create_index("status")
    contact_messages_col.create_index("created_at")
    contact_messages_col.create_index("email")
    career_applications_col.create_index("status")
    career_applications_col.create_index("created_at")
    career_applications_col.create_index("email")
    
    # Notification Indexes
    notifications_col.create_index("recipient_id")
    notifications_col.create_index("recipient_type")
    notifications_col.create_index("created_at")
    notification_logs_col.create_index("notification_id")
    notification_logs_col.create_index("delivery_type")


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)
