"""
SYRA Fresh - Order Model
"""
import random
import string
from datetime import datetime, timezone

ORDER_STATUS_FLOW = ["Placed", "Confirmed", "Packed", "Shipped", "Out for Delivery", "Delivered"]
CANCELABLE_STATUSES = {"Placed", "Confirmed", "Packed"}


def generate_order_number():
    date_part = datetime.now(timezone.utc).strftime("%y%m%d")
    rand_part = "".join(random.choices(string.digits, k=5))
    return f"SYRA{date_part}{rand_part}"


def new_order_doc(user_id, items, address, payment_method, totals, coupon_code=None, hub_id=None, hub_name=None):
    """
    items: list of {product_id, name, image, unit, price, quantity}
    totals: {subtotal, discount, delivery_fee, tax, total}
    hub_id/hub_name: Phase 2 - which serviceable hub this order was matched
        to (by delivery address city), so Hub Managers only ever see orders
        that belong to their own hub. May be None if the address city
        doesn't match any active hub (order is still valid; it just isn't
        visible to any Hub Manager, only the Super Admin).
    """
    now = datetime.now(timezone.utc)
    return {
        "order_number": generate_order_number(),
        "user_id": user_id,
        "items": items,
        "address": address,
        "payment_method": payment_method,   # "razorpay" | "cod"
        "payment_status": "pending" if payment_method == "razorpay" else "cod_pending",
        "razorpay_order_id": None,
        "razorpay_payment_id": None,
        "coupon_code": coupon_code,
        "totals": totals,
        "status": "Placed",
        "status_history": [{"status": "Placed", "at": now}],

        # Phase 2: hub routing
        "hub_id": hub_id,
        "hub_name": hub_name,

        # Delivery Boy Assignment
        "delivery_boy_id": None,
        "delivery_boy_name": None,
        "assigned_at": None,
        "assigned_by": None,
        
        "created_at": now,
        "updated_at": now,
    }


def serialize_order(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "order_number": doc.get("order_number"),
        "items": doc.get("items", []),
        "address": doc.get("address"),
        "payment_method": doc.get("payment_method"),
        "payment_status": doc.get("payment_status"),
        "totals": doc.get("totals"),
        "status": doc.get("status"),
        "hub_id": str(doc["hub_id"]) if doc.get("hub_id") else None,
        "hub_name": doc.get("hub_name"),
        "status_history": [
            {"status": h["status"], "at": h["at"].isoformat()} for h in doc.get("status_history", [])
        ],
        "delivery_boy_id": str(doc["delivery_boy_id"]) if doc.get("delivery_boy_id") else None,
        "delivery_boy_name": doc.get("delivery_boy_name"),
        "assigned_at": doc.get("assigned_at").isoformat() if doc.get("assigned_at") else None,
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
