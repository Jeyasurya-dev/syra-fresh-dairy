"""
SYRA Fresh - Admin Panel Routes
All routes below require a valid admin JWT (see utils.auth_utils.admin_required).

Auth:
  POST /api/admin/login

Dashboard:
  GET  /api/admin/dashboard

Products:
  GET    /api/admin/products
  POST   /api/admin/products
  PUT    /api/admin/products/<id>
  DELETE /api/admin/products/<id>
  POST   /api/admin/products/<id>/images   - upload one or more images
  PUT    /api/admin/products/<id>/stock    - quick stock update

Categories:
  POST   /api/admin/categories
  PUT    /api/admin/categories/<id>
  DELETE /api/admin/categories/<id>

Customers:
  GET /api/admin/customers

Orders:
  GET  /api/admin/orders
  PUT  /api/admin/orders/<id>/status
  POST /api/admin/orders/<id>/cancel

Coupons:
  GET/POST/PUT/DELETE /api/admin/coupons

Banners:
  GET/POST/DELETE /api/admin/banners

Reviews:
  GET /api/admin/reviews
  PUT /api/admin/reviews/<id>/approve
  DELETE /api/admin/reviews/<id>

Reports:
  GET /api/admin/reports/sales
"""
import os
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from bson import ObjectId
from bson.errors import InvalidId

from extensions import (
    admins_col, products_col, categories_col, users_col, orders_col,
    coupons_col, banners_col, reviews_col, verify_password,
)
from models.product import new_product_doc, serialize_product
from models.category import new_category_doc, serialize_category
from models.order import serialize_order, ORDER_STATUS_FLOW
from models.review import new_coupon_doc, serialize_coupon, serialize_review
from utils.validators import validate_product
from utils.auth_utils import issue_token, admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------- Auth ----------

@admin_bp.post("/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    admin = admins_col.find_one({"email": email})
    if not admin or not verify_password(password, admin["password_hash"]):
        return jsonify({"success": False, "message": "Invalid admin credentials"}), 401

    token = issue_token(admin["_id"], role="admin", expires=current_app.config["JWT_ADMIN_TOKEN_EXPIRES"])
    return jsonify({
        "success": True, "token": token,
        "admin": {"id": str(admin["_id"]), "name": admin.get("name"), "email": admin["email"]},
    }), 200


# ---------- Admin profile & password ----------
# BUG FIX / MISSING FEATURE: these two endpoints didn't exist at all, so the
# Settings page's "Admin Profile" and "Change Password" forms could only ever
# save to localStorage (clearly labelled as a stopgap in the UI). Adding the
# real endpoints here and wiring the frontend to them below.

@admin_bp.get("/me")
@admin_required
def admin_profile():
    admin = request.current_admin
    return jsonify({
        "success": True,
        "admin": {"id": str(admin["_id"]), "name": admin.get("name"), "email": admin.get("email")},
    }), 200


@admin_bp.put("/me")
@admin_required
def update_admin_profile():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400

    admins_col.update_one(
        {"_id": request.current_admin["_id"]},
        {"$set": {"name": name, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = admins_col.find_one({"_id": request.current_admin["_id"]})
    return jsonify({
        "success": True,
        "admin": {"id": str(updated["_id"]), "name": updated.get("name"), "email": updated.get("email")},
    }), 200


@admin_bp.post("/change-password")
@admin_required
def admin_change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields are required"}), 400
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters"}), 400

    admin = request.current_admin
    if not verify_password(current_password, admin.get("password_hash", "")):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400

    from extensions import hash_password
    admins_col.update_one(
        {"_id": admin["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    return jsonify({"success": True, "message": "Password updated successfully"}), 200


# ---------- Dashboard ----------

@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    total_orders = orders_col.count_documents({})
    total_customers = users_col.count_documents({})
    total_products = products_col.count_documents({})
    low_stock = products_col.count_documents({"stock": {"$lte": 5, "$gt": 0}})
    out_of_stock = products_col.count_documents({"stock": {"$lte": 0}})

    revenue_agg = list(orders_col.aggregate([
        {"$match": {"payment_status": {"$in": ["paid", "cod_pending"]}, "status": {"$ne": "Cancelled"}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$totals.total"}}},
    ]))
    total_revenue = revenue_agg[0]["revenue"] if revenue_agg else 0

    last_7_days = datetime.now(timezone.utc) - timedelta(days=7)
    daily_sales = list(orders_col.aggregate([
        {"$match": {"created_at": {"$gte": last_7_days}, "status": {"$ne": "Cancelled"}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "orders": {"$sum": 1}, "revenue": {"$sum": "$totals.total"},
        }},
        {"$sort": {"_id": 1}},
    ]))

    recent_orders = orders_col.find().sort("created_at", -1).limit(5)

    return jsonify({
        "success": True,
        "stats": {
            "total_orders": total_orders, "total_customers": total_customers,
            "total_products": total_products, "total_revenue": round(total_revenue, 2),
            "low_stock": low_stock, "out_of_stock": out_of_stock,
        },
        "daily_sales": daily_sales,
        "recent_orders": [serialize_order(o) for o in recent_orders],
    }), 200


# ---------- Products ----------

@admin_bp.get("/products")
@admin_required
def admin_list_products():
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(request.args.get("page_size", 20, type=int), 100)
    query = {}
    if request.args.get("category"):
        query["category"] = request.args["category"]
    total = products_col.count_documents(query)
    cursor = products_col.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    return jsonify({
        "success": True,
        "products": [serialize_product(p, detailed=True) for p in cursor],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }), 200


@admin_bp.post("/products")
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    errors = validate_product(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    doc = new_product_doc(data)
    result = products_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "product": serialize_product(doc, detailed=True)}), 201


@admin_bp.put("/products/<product_id>")
@admin_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    try:
        oid = ObjectId(product_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid product id"}), 400

    allowed = ["name", "description", "category", "subcategory", "price", "mrp",
               "unit", "stock", "tags", "is_featured", "is_bestseller", "is_active"]
    updates = {k: data[k] for k in allowed if k in data}
    if "price" in updates or "mrp" in updates:
        existing = products_col.find_one({"_id": oid})
        mrp = updates.get("mrp", existing.get("mrp"))
        price = updates.get("price", existing.get("price"))
        from models.product import _calc_discount
        updates["discount_percent"] = _calc_discount(mrp, price)
    updates["updated_at"] = datetime.now(timezone.utc)

    result = products_col.update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Product not found"}), 404
    updated = products_col.find_one({"_id": oid})
    return jsonify({"success": True, "product": serialize_product(updated, detailed=True)}), 200


@admin_bp.delete("/products/<product_id>")
@admin_required
def delete_product(product_id):
    try:
        result = products_col.delete_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid product id"}), 400
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True}), 200


@admin_bp.put("/products/<product_id>/stock")
@admin_required
def update_stock(product_id):
    data = request.get_json(silent=True) or {}
    try:
        stock = int(data.get("stock"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "stock must be an integer"}), 400
    try:
        result = products_col.update_one({"_id": ObjectId(product_id)}, {"$set": {"stock": stock}})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid product id"}), 400
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True}), 200


@admin_bp.post("/products/<product_id>/images")
@admin_required
def upload_product_images(product_id):
    try:
        oid = ObjectId(product_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid product id"}), 400

    files = request.files.getlist("images")
    if not files:
        return jsonify({"success": False, "message": "No images provided"}), 400

    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    saved_paths = []
    for f in files:
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
            continue
        filename = secure_filename(f"{product_id}_{datetime.now().timestamp()}.{ext}")
        f.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        saved_paths.append(f"/static/uploads/{filename}")

    if not saved_paths:
        return jsonify({"success": False, "message": "No valid image files (png/jpg/jpeg/webp only)"}), 400

    products_col.update_one({"_id": oid}, {"$push": {"images": {"$each": saved_paths}}})
    return jsonify({"success": True, "images": saved_paths}), 201


# ---------- Categories ----------

@admin_bp.get("/categories")
@admin_required
def admin_list_categories():
    """List ALL categories for the admin panel, including inactive ones.

    BUG FIX (documented gap in README): the admin Categories page used to
    call the public GET /api/categories, which only returns categories where
    is_active=True and doesn't include is_active/sort_order in the response.
    That meant deactivating a category made it disappear from the admin's
    own management screen with no way to see or re-activate it from the UI.
    """
    cats = categories_col.find().sort("sort_order", 1)
    return jsonify({"success": True, "categories": [serialize_category(c) for c in cats]}), 200


@admin_bp.post("/categories")
@admin_required
def create_category():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"success": False, "message": "Category name is required"}), 400
    doc = new_category_doc(data["name"], data.get("icon", ""), data.get("banner_image", ""),
                            data.get("subcategories", []), data.get("sort_order", 0))
    result = categories_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "category": serialize_category(doc)}), 201


@admin_bp.put("/categories/<category_id>")
@admin_required
def update_category(category_id):
    data = request.get_json(silent=True) or {}
    allowed = ["name", "icon", "banner_image", "subcategories", "sort_order", "is_active"]
    updates = {k: data[k] for k in allowed if k in data}
    try:
        result = categories_col.update_one({"_id": ObjectId(category_id)}, {"$set": updates})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid category id"}), 400
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Category not found"}), 404
    return jsonify({"success": True}), 200


@admin_bp.delete("/categories/<category_id>")
@admin_required
def delete_category(category_id):
    try:
        categories_col.delete_one({"_id": ObjectId(category_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid category id"}), 400
    return jsonify({"success": True}), 200


# ---------- Customers ----------

@admin_bp.get("/customers")
@admin_required
def list_customers():
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(request.args.get("page_size", 20, type=int), 100)
    total = users_col.count_documents({})
    cursor = users_col.find().sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    customers = []
    for u in cursor:
        order_count = orders_col.count_documents({"user_id": str(u["_id"])})
        customers.append({
            "id": str(u["_id"]), "name": u.get("name"), "email": u.get("email"),
            "phone": u.get("phone"), "order_count": order_count,
            "joined": u.get("created_at").isoformat() if u.get("created_at") else None,
            "is_active": u.get("is_active", True),
        })
    return jsonify({"success": True, "customers": customers,
                     "pagination": {"page": page, "page_size": page_size, "total": total}}), 200


# ---------- Orders ----------

@admin_bp.get("/orders")
@admin_required
def admin_list_orders():
    query = {}
    status = request.args.get("status")
    if status:
        query["status"] = status
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(request.args.get("page_size", 20, type=int), 100)
    total = orders_col.count_documents(query)
    cursor = orders_col.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    return jsonify({"success": True, "orders": [serialize_order(o) for o in cursor],
                     "pagination": {"page": page, "page_size": page_size, "total": total}}), 200


@admin_bp.put("/orders/<order_id>/status")
@admin_required
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ORDER_STATUS_FLOW:
        return jsonify({"success": False, "message": f"status must be one of {ORDER_STATUS_FLOW}"}), 400

    now = datetime.now(timezone.utc)
    try:
        result = orders_col.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": new_status, "updated_at": now},
             "$push": {"status_history": {"status": new_status, "at": now}}},
        )
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid order id"}), 400
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Order not found"}), 404
    return jsonify({"success": True}), 200


@admin_bp.post("/orders/<order_id>/cancel")
@admin_required
def admin_cancel_order(order_id):
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id)})
    except InvalidId:
        order = None
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404

    for item in order["items"]:
        products_col.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": item["quantity"]}})

    now = datetime.now(timezone.utc)
    orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {"status": "Cancelled", "updated_at": now},
         "$push": {"status_history": {"status": "Cancelled", "at": now}}},
    )
    return jsonify({"success": True}), 200


# ---------- Coupons ----------

@admin_bp.get("/coupons")
@admin_required
def list_coupons():
    return jsonify({"success": True, "coupons": [serialize_coupon(c) for c in coupons_col.find()]}), 200


@admin_bp.post("/coupons")
@admin_required
def create_coupon():
    data = request.get_json(silent=True) or {}
    if not data.get("code") or not data.get("discount_type") or data.get("value") is None:
        return jsonify({"success": False, "message": "code, discount_type and value are required"}), 400
    expires_at = None
    if data.get("expires_at"):
        expires_at = datetime.fromisoformat(data["expires_at"])
    doc = new_coupon_doc(data["code"], data["discount_type"], data["value"],
                          data.get("min_order_value", 0), data.get("max_discount"), expires_at)
    try:
        result = coupons_col.insert_one(doc)
    except Exception:
        return jsonify({"success": False, "message": "Coupon code already exists"}), 409
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "coupon": serialize_coupon(doc)}), 201


@admin_bp.put("/coupons/<coupon_id>")
@admin_required
def update_coupon(coupon_id):
    data = request.get_json(silent=True) or {}
    allowed = ["discount_type", "value", "min_order_value", "max_discount", "is_active"]
    updates = {k: data[k] for k in allowed if k in data}
    try:
        coupons_col.update_one({"_id": ObjectId(coupon_id)}, {"$set": updates})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid coupon id"}), 400
    return jsonify({"success": True}), 200


@admin_bp.delete("/coupons/<coupon_id>")
@admin_required
def delete_coupon(coupon_id):
    try:
        coupons_col.delete_one({"_id": ObjectId(coupon_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid coupon id"}), 400
    return jsonify({"success": True}), 200


# ---------- Banners ----------

@admin_bp.get("/banners")
@admin_required
def list_banners():
    banners = list(banners_col.find().sort("sort_order", 1))
    return jsonify({"success": True, "banners": [
        {"id": str(b["_id"]), "title": b.get("title"), "image": b.get("image"),
         "link": b.get("link"), "sort_order": b.get("sort_order", 0), "is_active": b.get("is_active", True)}
        for b in banners
    ]}), 200


@admin_bp.post("/banners")
@admin_required
def create_banner():
    data = request.get_json(silent=True) or {}
    if not data.get("image"):
        return jsonify({"success": False, "message": "image is required"}), 400
    doc = {
        "title": data.get("title", ""), "image": data["image"], "link": data.get("link", ""),
        "sort_order": data.get("sort_order", 0), "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = banners_col.insert_one(doc)
    return jsonify({"success": True, "banner_id": str(result.inserted_id)}), 201


@admin_bp.delete("/banners/<banner_id>")
@admin_required
def delete_banner(banner_id):
    try:
        banners_col.delete_one({"_id": ObjectId(banner_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid banner id"}), 400
    return jsonify({"success": True}), 200


# ---------- Review moderation ----------

@admin_bp.get("/reviews")
@admin_required
def admin_list_reviews():
    cursor = reviews_col.find().sort("created_at", -1)
    return jsonify({"success": True, "reviews": [serialize_review(r) for r in cursor]}), 200


@admin_bp.put("/reviews/<review_id>/approve")
@admin_required
def approve_review(review_id):
    try:
        reviews_col.update_one({"_id": ObjectId(review_id)}, {"$set": {"is_approved": True}})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid review id"}), 400
    return jsonify({"success": True}), 200


@admin_bp.delete("/reviews/<review_id>")
@admin_required
def delete_review(review_id):
    try:
        reviews_col.delete_one({"_id": ObjectId(review_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid review id"}), 400
    return jsonify({"success": True}), 200


# ---------- Reports ----------

@admin_bp.get("/reports/sales")
@admin_required
def sales_report():
    start = request.args.get("start")
    end = request.args.get("end")
    match = {"status": {"$ne": "Cancelled"}}
    if start or end:
        date_filter = {}
        if start:
            date_filter["$gte"] = datetime.fromisoformat(start)
        if end:
            date_filter["$lte"] = datetime.fromisoformat(end)
        match["created_at"] = date_filter

    report = list(orders_col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "orders": {"$sum": 1},
            "revenue": {"$sum": "$totals.total"},
            "items_sold": {"$sum": {"$sum": "$items.quantity"}},
        }},
        {"$sort": {"_id": 1}},
    ]))
    return jsonify({"success": True, "report": report}), 200
