"""
SYRA Fresh - User Model
MongoDB is schemaless, so this module defines the shape of a user
document plus helpers to build and serialize it consistently.
"""
from datetime import datetime, timezone
from bson import ObjectId


def new_user_doc(name, email, password_hash, phone=None):
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "phone": phone,
        "password_hash": password_hash,
        "role": "customer",
        "addresses": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True,
    }


def new_address_doc(label, full_name, phone, line1, line2, city, state, pincode, is_default=False):
    return {
        "_id": str(ObjectId()),
        "label": label or "Home",
        "full_name": full_name,
        "phone": phone,
        "line1": line1,
        "line2": line2 or "",
        "city": city,
        "state": state,
        "pincode": pincode,
        "is_default": is_default,
    }


def serialize_user(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "addresses": doc.get("addresses", []),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
