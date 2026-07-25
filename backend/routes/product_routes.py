"""
SYRA Fresh - Product & Category Routes (public, read-only)
GET /api/categories
GET /api/products                 - list with search/filter/sort/pagination
GET /api/products/<slug>          - single product detail
GET /api/products/featured
GET /api/products/bestsellers
GET /api/products/offers
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import products_col, categories_col
from models.product import serialize_product
from models.category import serialize_category

products_bp = Blueprint("products", __name__, url_prefix="/api")


@products_bp.get("/categories")
def list_categories():
    cats = categories_col.find({"is_active": True}).sort("sort_order", 1)
    return jsonify({"success": True, "categories": [serialize_category(c) for c in cats]}), 200


@products_bp.get("/products")
def list_products():
    query = {"is_active": True}

    category = request.args.get("category")
    if category:
        query["category"] = category

    subcategory = request.args.get("subcategory")
    if subcategory:
        query["subcategory"] = subcategory

    search = request.args.get("q")
    if search:
        query["$text"] = {"$search": search}

    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query["price"] = price_filter

    if request.args.get("in_stock") == "true":
        query["stock"] = {"$gt": 0}

    # Sorting
    sort_option = request.args.get("sort", "newest")
    sort_map = {
        "price_low": [("price", 1)],
        "price_high": [("price", -1)],
        "rating": [("rating_avg", -1)],
        "newest": [("created_at", -1)],
        "name": [("name", 1)],
    }
    sort_by = sort_map.get(sort_option, sort_map["newest"])

    # Pagination
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(request.args.get("page_size", 12, type=int), 60)
    skip = (page - 1) * page_size

    total = products_col.count_documents(query)
    cursor = products_col.find(query).sort(sort_by).skip(skip).limit(page_size)
    items = [serialize_product(p) for p in cursor]

    return jsonify({
        "success": True,
        "products": items,
        "pagination": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }), 200


@products_bp.get("/products/featured")
def featured_products():
    cursor = products_col.find({"is_active": True, "is_featured": True}).limit(12)
    return jsonify({"success": True, "products": [serialize_product(p) for p in cursor]}), 200


@products_bp.get("/products/bestsellers")
def bestseller_products():
    cursor = products_col.find({"is_active": True, "is_bestseller": True}).limit(12)
    return jsonify({"success": True, "products": [serialize_product(p) for p in cursor]}), 200


@products_bp.get("/products/offers")
def offer_products():
    cursor = products_col.find({"is_active": True, "discount_percent": {"$gte": 10}}) \
        .sort("discount_percent", -1).limit(12)
    return jsonify({"success": True, "products": [serialize_product(p) for p in cursor]}), 200


@products_bp.get("/products/<slug>")
def product_detail(slug):
    # Allow lookup by slug OR by ObjectId for flexibility from the frontend
    product = products_col.find_one({"slug": slug, "is_active": True})
    if not product:
        try:
            product = products_col.find_one({"_id": ObjectId(slug), "is_active": True})
        except InvalidId:
            product = None
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    related = products_col.find({
        "category": product["category"], "_id": {"$ne": product["_id"]}, "is_active": True,
    }).limit(6)

    return jsonify({
        "success": True,
        "product": serialize_product(product, detailed=True),
        "related_products": [serialize_product(p) for p in related],
    }), 200
