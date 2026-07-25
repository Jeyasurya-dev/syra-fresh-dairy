"""
SYRA Fresh - Review Routes
GET  /api/products/<product_id>/reviews
POST /api/products/<product_id>/reviews
"""
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request, jsonify

from extensions import reviews_col, products_col
from models.review import new_review_doc, serialize_review
from utils.auth_utils import login_required

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/products")


@reviews_bp.get("/<product_id>/reviews")
def list_reviews(product_id):
    cursor = reviews_col.find({"product_id": product_id, "is_approved": True}).sort("created_at", -1)
    return jsonify({"success": True, "reviews": [serialize_review(r) for r in cursor]}), 200


@reviews_bp.post("/<product_id>/reviews")
@login_required
def add_review(product_id):
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    comment = (data.get("comment") or "").strip()

    if not rating or not (1 <= int(rating) <= 5) or not comment:
        return jsonify({"success": False, "message": "A rating (1-5) and comment are required"}), 400

    try:
        product = products_col.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        product = None
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    doc = new_review_doc(product_id, str(request.current_user["_id"]), request.current_user["name"], rating, comment)
    try:
        reviews_col.insert_one(doc)
    except Exception:
        return jsonify({"success": False, "message": "You have already reviewed this product"}), 409

    # Recalculate rolling average rating
    agg = list(reviews_col.aggregate([
        {"$match": {"product_id": product_id, "is_approved": True}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]))
    if agg:
        products_col.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"rating_avg": agg[0]["avg"], "rating_count": agg[0]["count"]}},
        )

    return jsonify({"success": True, "review": serialize_review(doc)}), 201
