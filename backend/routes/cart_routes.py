"""
SYRA Fresh - Cart & Wishlist Routes
GET    /api/cart
POST   /api/cart/items                - add item {product_id, quantity}
PUT    /api/cart/items/<product_id>   - update quantity
DELETE /api/cart/items/<product_id>
DELETE /api/cart                      - clear cart

GET    /api/wishlist
POST   /api/wishlist/<product_id>
DELETE /api/wishlist/<product_id>
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import carts_col, wishlists_col, products_col
from models.product import serialize_product
from utils.auth_utils import login_required

cart_bp = Blueprint("cart", __name__, url_prefix="/api")


def _get_or_create_cart(user_id):
    cart = carts_col.find_one({"user_id": user_id})
    if not cart:
        cart_id = carts_col.insert_one({"user_id": user_id, "items": []}).inserted_id
        cart = carts_col.find_one({"_id": cart_id})
    return cart


def _hydrate_cart(cart):
    """Attach live product data (price/stock/image) to each cart line."""
    lines = []
    subtotal = 0.0
    for item in cart.get("items", []):
        try:
            product = products_col.find_one({"_id": ObjectId(item["product_id"]), "is_active": True})
        except InvalidId:
            product = None
        if not product:
            continue
        line_total = product["price"] * item["quantity"]
        subtotal += line_total
        lines.append({
            "product": serialize_product(product),
            "quantity": item["quantity"],
            "line_total": round(line_total, 2),
        })
    return {"items": lines, "subtotal": round(subtotal, 2), "item_count": sum(l["quantity"] for l in lines)}


@cart_bp.get("/cart")
@login_required
def get_cart():
    cart = _get_or_create_cart(str(request.current_user["_id"]))
    return jsonify({"success": True, "cart": _hydrate_cart(cart)}), 200


@cart_bp.post("/cart/items")
@login_required
def add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = max(int(data.get("quantity", 1)), 1)

    if not product_id:
        return jsonify({"success": False, "message": "product_id is required"}), 400
    try:
        product = products_col.find_one({"_id": ObjectId(product_id), "is_active": True})
    except InvalidId:
        product = None
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404
    if product.get("stock", 0) < quantity:
        return jsonify({"success": False, "message": "Not enough stock available"}), 409

    user_id = str(request.current_user["_id"])
    cart = _get_or_create_cart(user_id)

    existing = next((i for i in cart["items"] if i["product_id"] == product_id), None)
    if existing:
        carts_col.update_one(
            {"_id": cart["_id"], "items.product_id": product_id},
            {"$inc": {"items.$.quantity": quantity}},
        )
    else:
        carts_col.update_one(
            {"_id": cart["_id"]},
            {"$push": {"items": {"product_id": product_id, "quantity": quantity}}},
        )

    cart = carts_col.find_one({"_id": cart["_id"]})
    return jsonify({"success": True, "cart": _hydrate_cart(cart)}), 200


@cart_bp.put("/cart/items/<product_id>")
@login_required
def update_cart_item(product_id):
    data = request.get_json(silent=True) or {}
    quantity = int(data.get("quantity", 1))
    user_id = str(request.current_user["_id"])
    cart = _get_or_create_cart(user_id)

    if quantity <= 0:
        carts_col.update_one({"_id": cart["_id"]}, {"$pull": {"items": {"product_id": product_id}}})
    else:
        result = carts_col.update_one(
            {"_id": cart["_id"], "items.product_id": product_id},
            {"$set": {"items.$.quantity": quantity}},
        )
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Item not in cart"}), 404

    cart = carts_col.find_one({"_id": cart["_id"]})
    return jsonify({"success": True, "cart": _hydrate_cart(cart)}), 200


@cart_bp.delete("/cart/items/<product_id>")
@login_required
def remove_cart_item(product_id):
    user_id = str(request.current_user["_id"])
    cart = _get_or_create_cart(user_id)
    carts_col.update_one({"_id": cart["_id"]}, {"$pull": {"items": {"product_id": product_id}}})
    cart = carts_col.find_one({"_id": cart["_id"]})
    return jsonify({"success": True, "cart": _hydrate_cart(cart)}), 200


@cart_bp.delete("/cart")
@login_required
def clear_cart():
    carts_col.update_one({"user_id": str(request.current_user["_id"])}, {"$set": {"items": []}})
    return jsonify({"success": True}), 200


# ---------- Wishlist ----------

@cart_bp.get("/wishlist")
@login_required
def get_wishlist():
    doc = wishlists_col.find_one({"user_id": str(request.current_user["_id"])}) or {"product_ids": []}
    ids = []
    for pid in doc.get("product_ids", []):
        try:
            ids.append(ObjectId(pid))
        except InvalidId:
            continue
    products = products_col.find({"_id": {"$in": ids}, "is_active": True})
    return jsonify({"success": True, "products": [serialize_product(p) for p in products]}), 200


@cart_bp.post("/wishlist/<product_id>")
@login_required
def add_to_wishlist(product_id):
    user_id = str(request.current_user["_id"])
    wishlists_col.update_one(
        {"user_id": user_id}, {"$addToSet": {"product_ids": product_id}}, upsert=True,
    )
    return jsonify({"success": True}), 200


@cart_bp.delete("/wishlist/<product_id>")
@login_required
def remove_from_wishlist(product_id):
    user_id = str(request.current_user["_id"])
    wishlists_col.update_one({"user_id": user_id}, {"$pull": {"product_ids": product_id}})
    return jsonify({"success": True}), 200
