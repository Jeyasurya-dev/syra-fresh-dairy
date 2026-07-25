"""
SYRA Fresh - Admin District Management Routes (Phase 2)
GET    /api/admin/districts
POST   /api/admin/districts
PUT    /api/admin/districts/<district_id>
DELETE /api/admin/districts/<district_id>   (blocked if the district still has hubs)
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import districts_col, hubs_col
from models.district import new_district_doc, serialize_district
from utils.auth_utils import admin_required

admin_district_bp = Blueprint("admin_district", __name__, url_prefix="/api/admin/districts")


@admin_district_bp.get("")
@admin_required
def list_districts():
    districts = list(districts_col.find().sort("name", 1))
    out = []
    for d in districts:
        hub_count = hubs_col.count_documents({"district_id": d["_id"]})
        out.append(serialize_district(d, hub_count=hub_count))
    return jsonify({"success": True, "districts": out}), 200


@admin_district_bp.post("")
@admin_required
def create_district():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "District name is required"}), 400

    doc = new_district_doc(name, data.get("state", "Tamil Nadu"))
    try:
        result = districts_col.insert_one(doc)
    except Exception:
        return jsonify({"success": False, "message": "A district with this name already exists"}), 409
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "district": serialize_district(doc, hub_count=0)}), 201


@admin_district_bp.put("/<district_id>")
@admin_required
def update_district(district_id):
    data = request.get_json(silent=True) or {}
    allowed = ["name", "state", "is_active"]
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    updates["updated_at"] = datetime.now(timezone.utc)

    try:
        oid = ObjectId(district_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid district id"}), 400

    result = districts_col.update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "District not found"}), 404

    updated = districts_col.find_one({"_id": oid})
    # Keep hub_manager/hub district_name in sync if the district was renamed
    if "name" in updates:
        hubs_col.update_many({"district_id": oid}, {"$set": {"district_name": updates["name"]}})

    hub_count = hubs_col.count_documents({"district_id": oid})
    return jsonify({"success": True, "district": serialize_district(updated, hub_count=hub_count)}), 200


@admin_district_bp.delete("/<district_id>")
@admin_required
def delete_district(district_id):
    try:
        oid = ObjectId(district_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid district id"}), 400

    if hubs_col.count_documents({"district_id": oid}) > 0:
        return jsonify({
            "success": False,
            "message": "Cannot delete a district that still has hubs. Delete or reassign its hubs first."
        }), 409

    result = districts_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "District not found"}), 404
    return jsonify({"success": True}), 200
