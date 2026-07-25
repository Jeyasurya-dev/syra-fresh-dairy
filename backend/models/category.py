"""
SYRA Fresh - Category Model
"""
from datetime import datetime, timezone
from models.product import slugify


def new_category_doc(name, icon="", banner_image="", subcategories=None, sort_order=0):
    return {
        "name": name.strip(),
        "slug": slugify(name),
        "icon": icon,
        "banner_image": banner_image,
        "subcategories": subcategories or [],
        "sort_order": sort_order,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_category(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "slug": doc.get("slug"),
        "icon": doc.get("icon"),
        "banner_image": doc.get("banner_image"),
        "subcategories": doc.get("subcategories", []),
        # BUG FIX: these were missing entirely, so the admin Categories page
        # could never show (or reliably edit-and-confirm) a category's real
        # active/inactive state or its sort order after a page reload.
        "sort_order": doc.get("sort_order", 0),
        "is_active": doc.get("is_active", True),
    }


# Seed data matching the SYRA Fresh catalog brief
DEFAULT_CATEGORIES = [
    {
        "name": "Dairy Products",
        "icon": "🥛",
        "subcategories": ["Milk", "Curd", "Yogurt", "Greek Yogurt", "Buttermilk", "Lassi",
                           "Butter", "Ghee", "Paneer", "Cheese", "Cream", "Milk Powder", "Flavoured Milk"],
    },
    {
        "name": "Ice Cream",
        "icon": "🍦",
        "subcategories": ["Vanilla", "Chocolate", "Strawberry", "Mango", "Butterscotch",
                           "Black Currant", "Pista", "Coffee", "Cookies & Cream", "Belgian Chocolate",
                           "Kulfi", "Cassata", "Sundae", "Family Pack", "Cone", "Cup", "Stick", "Popsicle"],
    },
    {
        "name": "Healthy Snacks",
        "icon": "🥜",
        "subcategories": ["Mixed Nuts", "Almonds", "Cashews", "Walnuts", "Pistachios", "Dates",
                           "Raisins", "Seeds", "Granola", "Muesli", "Oats", "Protein Bars",
                           "Energy Bars", "Millet Cookies", "Roasted Snacks"],
    },
    {
        "name": "Fresh Fruits",
        "icon": "🍎",
        "subcategories": ["Apple", "Banana", "Orange", "Mango", "Grapes", "Pomegranate", "Guava",
                           "Papaya", "Watermelon", "Pineapple", "Kiwi", "Dragon Fruit", "Avocado",
                           "Strawberry", "Blueberry", "Coconut"],
    },
]
