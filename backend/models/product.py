"""
SYRA Fresh - Product Model
"""
import re
from datetime import datetime, timezone


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def new_product_doc(data):
    """Build a product document from validated input dict."""
    name = data["name"].strip()
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "slug": slugify(name) + "-" + str(int(now.timestamp()))[-5:],
        "description": data.get("description", "").strip(),
        "category": data["category"],          # e.g. "dairy"
        "subcategory": data.get("subcategory", ""),  # e.g. "Paneer"
        "price": float(data["price"]),
        "mrp": float(data.get("mrp", data["price"])),
        "discount_percent": _calc_discount(data.get("mrp", data["price"]), data["price"]),
        "unit": data.get("unit", "1 pc"),        # e.g. "500 ml", "1 kg"
        "stock": int(data.get("stock", 0)),
        "images": data.get("images", []),        # list of URLs / static paths
        "tags": data.get("tags", []),
        "is_featured": bool(data.get("is_featured", False)),
        "is_bestseller": bool(data.get("is_bestseller", False)),
        "is_active": True,
        "rating_avg": 0.0,
        "rating_count": 0,
        "created_at": now,
        "updated_at": now,
    }


def _calc_discount(mrp, price):
    try:
        mrp = float(mrp)
        price = float(price)
        if mrp <= 0 or price >= mrp:
            return 0
        return round(((mrp - price) / mrp) * 100)
    except (TypeError, ValueError):
        return 0


def serialize_product(doc, detailed=False):
    if not doc:
        return None
    out = {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "slug": doc.get("slug"),
        "category": doc.get("category"),
        "subcategory": doc.get("subcategory"),
        "price": doc.get("price"),
        "mrp": doc.get("mrp"),
        "discount_percent": doc.get("discount_percent", 0),
        "unit": doc.get("unit"),
        "in_stock": doc.get("stock", 0) > 0,
        "stock": doc.get("stock", 0),
        "images": doc.get("images", []),
        "is_featured": doc.get("is_featured", False),
        "is_bestseller": doc.get("is_bestseller", False),
        "rating_avg": round(doc.get("rating_avg", 0), 1),
        "rating_count": doc.get("rating_count", 0),
    }
    if detailed:
        out["description"] = doc.get("description")
        out["tags"] = doc.get("tags", [])
    return out
