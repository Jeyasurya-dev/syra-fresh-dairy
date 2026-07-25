"""
SYRA Fresh - District Model (Phase 2: District -> Hub -> Hub Manager)
"""
from datetime import datetime, timezone
from models.product import slugify

# Phase 1 rollout districts, each with exactly three hubs, per the
# architecture brief. Used by seed.py to populate districts_col/hubs_col.
PHASE1_DISTRICTS = [
    {"name": "Tenkasi", "hubs": ["Tenkasi", "Sankarankovil", "Alangulam"]},
    {"name": "Tirunelveli", "hubs": ["Tirunelveli", "Palayamkottai", "Valliyur"]},
    {"name": "Thoothukudi", "hubs": ["Thoothukudi", "Kovilpatti", "Tiruchendur"]},
    {"name": "Madurai", "hubs": ["Madurai", "Thirumangalam", "Melur"]},
    {"name": "Virudhunagar", "hubs": ["Virudhunagar", "Sivakasi", "Rajapalayam"]},
    {"name": "Kanyakumari", "hubs": ["Nagercoil", "Marthandam", "Kuzhithurai"]},
]


def new_district_doc(name, state="Tamil Nadu", is_active=True):
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "slug": slugify(name),
        "state": state,
        "is_active": is_active,
        "created_at": now,
        "updated_at": now,
    }


def serialize_district(doc, hub_count=None):
    if not doc:
        return None
    out = {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "slug": doc.get("slug"),
        "state": doc.get("state"),
        "is_active": doc.get("is_active", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
    if hub_count is not None:
        out["hub_count"] = hub_count
    return out
