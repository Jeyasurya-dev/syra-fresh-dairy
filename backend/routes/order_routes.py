"""
SYRA Fresh - Orders & Checkout Routes
POST /api/orders/checkout        - create order (COD immediate, Razorpay creates a pending order)
POST /api/orders/verify-payment  - verify Razorpay signature and confirm order
GET  /api/orders                 - order history for logged-in customer
GET  /api/orders/<order_id>      - single order (tracking)
POST /api/orders/<order_id>/cancel
"""
import hmac
import hashlib
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request, jsonify, current_app

from extensions import orders_col, carts_col, products_col, coupons_col, hubs_col
from models.order import new_order_doc, serialize_order, CANCELABLE_STATUSES
from utils.auth_utils import login_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def _match_hub_for_address(address):
    """Phase 2: route an order to a serviceable hub by matching the delivery
    address city against the hub names seeded from the District -> Hub
    architecture (each hub is named after a town, e.g. "Sankarankovil").
    Case-insensitive exact match; returns (hub_id, hub_name) or (None, None)
    if the address is outside the current rollout districts. An unmatched
    order is not an error - it just isn't visible to any Hub Manager, only
    the Super Admin (who can see every order regardless of hub).
    """
    city = (address or {}).get("city", "").strip()
    if not city:
        return None, None
    hub = hubs_col.find_one({"name": {"$regex": f"^{city}$", "$options": "i"}, "is_active": True})
    if not hub:
        return None, None
    return hub["_id"], hub["name"]


def _apply_coupon(subtotal, code):
    if not code:
        return 0, None
    coupon = coupons_col.find_one({"code": code.strip().upper(), "is_active": True})
    if not coupon or subtotal < coupon.get("min_order_value", 0):
        return 0, None
    if coupon["discount_type"] == "percent":
        discount = subtotal * (coupon["value"] / 100)
        if coupon.get("max_discount"):
            discount = min(discount, coupon["max_discount"])
    else:
        discount = coupon["value"]
    return round(min(discount, subtotal), 2), coupon["code"]


def _build_order_items_from_cart(cart):
    items = []
    subtotal = 0.0
    for line in cart.get("items", []):
        try:
            product = products_col.find_one({"_id": ObjectId(line["product_id"]), "is_active": True})
        except InvalidId:
            product = None
        if not product or product.get("stock", 0) < line["quantity"]:
            continue
        line_total = product["price"] * line["quantity"]
        subtotal += line_total
        items.append({
            "product_id": str(product["_id"]),
            "name": product["name"],
            "image": (product.get("images") or [None])[0],
            "unit": product.get("unit"),
            "price": product["price"],
            "quantity": line["quantity"],
        })
    return items, round(subtotal, 2)


@orders_bp.post("/checkout")
@login_required
def checkout():
    data = request.get_json(silent=True) or {}
    address = data.get("address")
    payment_method = data.get("payment_method")  # "razorpay" | "cod"
    coupon_code = data.get("coupon_code")

    if not address or payment_method not in ("razorpay", "cod"):
        return jsonify({"success": False, "message": "Address and a valid payment method are required"}), 400

    user_id = str(request.current_user["_id"])
    cart = carts_col.find_one({"user_id": user_id})
    if not cart or not cart.get("items"):
        return jsonify({"success": False, "message": "Your cart is empty"}), 400

    items, subtotal = _build_order_items_from_cart(cart)
    if not items:
        return jsonify({"success": False, "message": "Items in your cart are no longer available"}), 409

    discount, applied_code = _apply_coupon(subtotal, coupon_code)
    delivery_fee = 0 if subtotal >= current_app.config["FREE_DELIVERY_THRESHOLD"] else current_app.config["DELIVERY_FEE"]
    total = round(subtotal - discount + delivery_fee, 2)

    totals = {
        "subtotal": subtotal, "discount": discount,
        "delivery_fee": delivery_fee, "total": total,
    }

    hub_id, hub_name = _match_hub_for_address(address)
    order_doc = new_order_doc(user_id, items, address, payment_method, totals, applied_code, hub_id, hub_name)
    result = orders_col.insert_one(order_doc)

    if payment_method == "cod":
        # Deduct stock immediately for COD orders
        for item in items:
            products_col.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": -item["quantity"]}})
        carts_col.update_one({"_id": cart["_id"]}, {"$set": {"items": []}})
        order_doc["_id"] = result.inserted_id
        return jsonify({"success": True, "order": serialize_order(order_doc), "requires_payment": False}), 201

    # Razorpay flow: frontend calls Razorpay checkout with this order info,
    # stock is deducted only after payment is verified.
    razorpay_order = {
        "id": f"order_{str(result.inserted_id)[-12:]}",
        "amount": int(total * 100),  # paise
        "currency": "INR",
        "key_id": current_app.config["RAZORPAY_KEY_ID"],
    }
    orders_col.update_one({"_id": result.inserted_id}, {"$set": {"razorpay_order_id": razorpay_order["id"]}})

    return jsonify({
        "success": True, "order_id": str(result.inserted_id),
        "requires_payment": True, "razorpay": razorpay_order,
    }), 201


@orders_bp.post("/verify-payment")
@login_required
def verify_payment():
    """
    Verifies the Razorpay signature: HMAC-SHA256(order_id + '|' + payment_id, key_secret)
    must equal the signature Razorpay returns to the frontend after payment.
    """
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")

    if not all([order_id, razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({"success": False, "message": "Missing payment verification fields"}), 400

    try:
        order = orders_col.find_one({"_id": ObjectId(order_id), "user_id": str(request.current_user["_id"])})
    except InvalidId:
        order = None
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404

    payload = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_signature = hmac.new(
        current_app.config["RAZORPAY_KEY_SECRET"].encode(), payload, hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        orders_col.update_one({"_id": order["_id"]}, {"$set": {"payment_status": "failed"}})
        return jsonify({"success": False, "message": "Payment verification failed"}), 400

    for item in order["items"]:
        products_col.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": -item["quantity"]}})
    carts_col.update_one({"user_id": order["user_id"]}, {"$set": {"items": []}})

    orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {"payment_status": "paid", "razorpay_payment_id": razorpay_payment_id}},
    )
    updated = orders_col.find_one({"_id": order["_id"]})
    return jsonify({"success": True, "order": serialize_order(updated)}), 200


@orders_bp.get("")
@login_required
def order_history():
    cursor = orders_col.find({"user_id": str(request.current_user["_id"])}).sort("created_at", -1)
    return jsonify({"success": True, "orders": [serialize_order(o) for o in cursor]}), 200


@orders_bp.get("/<order_id>")
@login_required
def order_detail(order_id):
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id), "user_id": str(request.current_user["_id"])})
    except InvalidId:
        order = None
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    return jsonify({"success": True, "order": serialize_order(order)}), 200


@orders_bp.post("/<order_id>/cancel")
@login_required
def cancel_order(order_id):
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id), "user_id": str(request.current_user["_id"])})
    except InvalidId:
        order = None
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    if order["status"] not in CANCELABLE_STATUSES:
        return jsonify({"success": False, "message": f"Order cannot be cancelled once {order['status']}"}), 409

    for item in order["items"]:
        products_col.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": item["quantity"]}})

    from datetime import datetime, timezone
    orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {"status": "Cancelled", "updated_at": datetime.now(timezone.utc)},
         "$push": {"status_history": {"status": "Cancelled", "at": datetime.now(timezone.utc)}}},
    )
    return jsonify({"success": True}), 200
