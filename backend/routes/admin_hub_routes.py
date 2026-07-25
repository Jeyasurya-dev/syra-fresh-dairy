"""
SYRA Fresh - Admin Hub Management Routes (Phase 2)
GET    /api/admin/hubs                 - list all hubs (optionally ?district_id=)
POST   /api/admin/hubs                 - create a hub under a district
PUT    /api/admin/hubs/<hub_id>
DELETE /api/admin/hubs/<hub_id>        - blocked if it still has a manager or delivery boys
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import hubs_col, districts_col, hub_managers_col, delivery_boys_col
from models.hub import new_hub_doc, serialize_hub
from utils.auth_utils import admin_required

admin_hub_bp = Blueprint("admin_hub", __name__, url_prefix="/api/admin/hubs")


@admin_hub_bp.get("")
@admin_required
def list_hubs():
    query = {}
    district_id = request.args.get("district_id")
    if district_id:
        try:
            query["district_id"] = ObjectId(district_id)
        except InvalidId:
            return jsonify({"success": False, "message": "Invalid district id"}), 400

    hubs = list(hubs_col.find(query).sort("name", 1))
    out = []
    for h in hubs:
        delivery_boy_count = delivery_boys_col.count_documents({"hub_id": h["_id"]})
        manager = hub_managers_col.find_one({"hub_id": h["_id"]})
        out.append(serialize_hub(h, delivery_boy_count=delivery_boy_count, hub_manager=manager))
    return jsonify({"success": True, "hubs": out}), 200


@admin_hub_bp.post("")
@admin_required
def create_hub():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    district_id = data.get("district_id")
    if not name or not district_id:
        return jsonify({"success": False, "message": "Hub name and district_id are required"}), 400

    try:
        district = districts_col.find_one({"_id": ObjectId(district_id)})
    except InvalidId:
        district = None
    if not district:
        return jsonify({"success": False, "message": "District not found"}), 404

    doc = new_hub_doc(name, district["_id"], district["name"])
    try:
        result = hubs_col.insert_one(doc)
    except Exception:
        return jsonify({"success": False, "message": "A hub with this name already exists in this district"}), 409
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "hub": serialize_hub(doc, delivery_boy_count=0, hub_manager=None)}), 201


@admin_hub_bp.put("/<hub_id>")
@admin_required
def update_hub(hub_id):
    data = request.get_json(silent=True) or {}
    try:
        oid = ObjectId(hub_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub id"}), 400

    updates = {}
    if "name" in data:
        updates["name"] = data["name"].strip()
    if "is_active" in data:
        updates["is_active"] = bool(data["is_active"])
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    updates["updated_at"] = datetime.now(timezone.utc)

    result = hubs_col.update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Hub not found"}), 404

    updated = hubs_col.find_one({"_id": oid})
    delivery_boy_count = delivery_boys_col.count_documents({"hub_id": oid})
    manager = hub_managers_col.find_one({"hub_id": oid})
    return jsonify({"success": True, "hub": serialize_hub(updated, delivery_boy_count=delivery_boy_count, hub_manager=manager)}), 200


@admin_hub_bp.delete("/<hub_id>")
@admin_required
def delete_hub(hub_id):
    try:
        oid = ObjectId(hub_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub id"}), 400

    if hub_managers_col.count_documents({"hub_id": oid}) > 0:
        return jsonify({"success": False, "message": "This hub still has a Hub Manager assigned. Remove them first."}), 409
    if delivery_boys_col.count_documents({"hub_id": oid}) > 0:
        return jsonify({"success": False, "message": "This hub still has delivery boys assigned. Transfer them first."}), 409

    result = hubs_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Hub not found"}), 404
    return jsonify({"success": True}), 200
