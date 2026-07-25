"""
SYRA Fresh - Review & Coupon Models
"""
from datetime import datetime, timezone


def new_review_doc(product_id, user_id, user_name, rating, comment):
    return {
        "product_id": product_id,
        "user_id": user_id,
        "user_name": user_name,
        "rating": int(rating),
        "comment": comment.strip(),
        "is_approved": True,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_review(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "user_name": doc.get("user_name"),
        "rating": doc.get("rating"),
        "comment": doc.get("comment"),
        # BUG FIX: was missing, so the admin Reviews page had no way to know
        # which reviews were already approved after a page reload (it faked
        # this with an in-memory-only Set that reset on every refresh).
        "is_approved": doc.get("is_approved", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }


def new_coupon_doc(code, discount_type, value, min_order_value=0, max_discount=None, expires_at=None):
    return {
        "code": code.strip().upper(),
        "discount_type": discount_type,   # "percent" | "flat"
        "value": float(value),
        "min_order_value": float(min_order_value),
        "max_discount": max_discount,
        "expires_at": expires_at,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_coupon(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "code": doc.get("code"),
        "discount_type": doc.get("discount_type"),
        "value": doc.get("value"),
        "min_order_value": doc.get("min_order_value"),
        "max_discount": doc.get("max_discount"),
        "expires_at": doc.get("expires_at").isoformat() if doc.get("expires_at") else None,
        "is_active": doc.get("is_active", True),
    }
