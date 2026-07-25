"""
SYRA Fresh - Hub Model (Phase 2: District -> Hub -> Hub Manager)
Each hub belongs to exactly one district, has at most one hub manager
(enforced by the unique sparse index on hub_managers_col.hub_id), and can
have many delivery boys (delivery_boys_col.hub_id).
"""
from datetime import datetime, timezone
from models.product import slugify


def new_hub_doc(name, district_id, district_name, is_active=True):
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "slug": slugify(f"{district_name}-{name}"),
        "district_id": district_id,
        "district_name": district_name,
        "is_active": is_active,
        "created_at": now,
        "updated_at": now,
    }


def serialize_hub(doc, delivery_boy_count=None, hub_manager=None):
    if not doc:
        return None
    out = {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "slug": doc.get("slug"),
        "district_id": str(doc.get("district_id")) if doc.get("district_id") else None,
        "district_name": doc.get("district_name"),
        "is_active": doc.get("is_active", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
    if delivery_boy_count is not None:
        out["delivery_boy_count"] = delivery_boy_count
    if hub_manager is not None:
        out["hub_manager"] = {
            "id": str(hub_manager["_id"]),
            "name": hub_manager.get("name"),
            "email": hub_manager.get("email"),
        } if hub_manager else None
    return out
