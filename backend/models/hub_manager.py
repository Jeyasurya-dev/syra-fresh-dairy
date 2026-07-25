"""
SYRA Fresh - Hub Manager Model (Phase 2)
Hub Managers are created by the Super Admin (no public self-registration,
unlike delivery boys) and are scoped to exactly one hub. RBAC enforcement
happens in utils.auth_utils.hub_manager_required, which attaches
request.current_hub_manager and its hub_id to every protected route.
"""
from datetime import datetime, timezone


def new_hub_manager_doc(name, email, mobile, password_hash, hub_id, hub_name, district_name):
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "mobile": mobile.strip(),
        "password_hash": password_hash,
        "role": "hub_manager",
        "hub_id": hub_id,
        "hub_name": hub_name,
        "district_name": district_name,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


def serialize_hub_manager(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "mobile": doc.get("mobile"),
        "hub_id": str(doc.get("hub_id")) if doc.get("hub_id") else None,
        "hub_name": doc.get("hub_name"),
        "district_name": doc.get("district_name"),
        "is_active": doc.get("is_active", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
