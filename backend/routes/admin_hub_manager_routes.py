"""
SYRA Fresh - Admin Hub Manager Management Routes (Phase 2)
GET    /api/admin/hub-managers
POST   /api/admin/hub-managers                       - create a Hub Manager account for a hub
PUT    /api/admin/hub-managers/<id>
POST   /api/admin/hub-managers/<id>/enable
POST   /api/admin/hub-managers/<id>/disable
DELETE /api/admin/hub-managers/<id>

Hub Managers are created by the Super Admin only - there is no public
self-registration for this role (unlike delivery boys), since a hub can
only ever have one manager (enforced by the unique sparse index on
hub_managers_col.hub_id).
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import hub_managers_col, hubs_col, hash_password
from models.hub_manager import new_hub_manager_doc, serialize_hub_manager
from utils.validators import is_valid_email, is_valid_mobile, is_strong_password
from utils.auth_utils import admin_required

admin_hub_manager_bp = Blueprint("admin_hub_manager", __name__, url_prefix="/api/admin/hub-managers")


@admin_hub_manager_bp.get("")
@admin_required
def list_hub_managers():
    managers = list(hub_managers_col.find().sort("created_at", -1))
    return jsonify({"success": True, "hub_managers": [serialize_hub_manager(m) for m in managers]}), 200


@admin_hub_manager_bp.post("")
@admin_required
def create_hub_manager():
    data = request.get_json(silent=True) or {}
    errors = {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    mobile = (data.get("mobile") or "").strip()
    password = data.get("password") or ""
    hub_id = data.get("hub_id")

    if not name:
        errors["name"] = "Name is required"
    if not is_valid_email(email):
        errors["email"] = "Enter a valid email address"
    if not is_valid_mobile(mobile):
        errors["mobile"] = "Enter a valid 10-digit mobile number"
    if not is_strong_password(password):
        errors["password"] = "Password must be at least 8 characters with a letter and a number"
    if not hub_id:
        errors["hub_id"] = "Hub is required"
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    try:
        hub = hubs_col.find_one({"_id": ObjectId(hub_id)})
    except InvalidId:
        hub = None
    if not hub:
        return jsonify({"success": False, "errors": {"hub_id": "Hub not found"}}), 404

    if hub_managers_col.find_one({"email": email}):
        return jsonify({"success": False, "errors": {"email": "Email already registered"}}), 409
    if hub_managers_col.find_one({"hub_id": hub["_id"]}):
        return jsonify({"success": False, "errors": {"hub_id": "This hub already has a Hub Manager. Remove them before assigning a new one."}}), 409

    doc = new_hub_manager_doc(name, email, mobile, hash_password(password), hub["_id"], hub["name"], hub.get("district_name"))
    result = hub_managers_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "hub_manager": serialize_hub_manager(doc)}), 201


@admin_hub_manager_bp.put("/<manager_id>")
@admin_required
def update_hub_manager(manager_id):
    data = request.get_json(silent=True) or {}
    try:
        oid = ObjectId(manager_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub manager id"}), 400

    manager = hub_managers_col.find_one({"_id": oid})
    if not manager:
        return jsonify({"success": False, "message": "Hub Manager not found"}), 404

    updates = {}
    if data.get("name"):
        updates["name"] = data["name"].strip()
    if data.get("mobile"):
        if not is_valid_mobile(data["mobile"]):
            return jsonify({"success": False, "message": "Enter a valid 10-digit mobile number"}), 400
        updates["mobile"] = data["mobile"].strip()

    # Reassigning a manager to a different hub - allowed as long as the
    # target hub doesn't already have one.
    if data.get("hub_id"):
        try:
            new_hub = hubs_col.find_one({"_id": ObjectId(data["hub_id"])})
        except InvalidId:
            new_hub = None
        if not new_hub:
            return jsonify({"success": False, "message": "Hub not found"}), 404
        existing = hub_managers_col.find_one({"hub_id": new_hub["_id"], "_id": {"$ne": oid}})
        if existing:
            return jsonify({"success": False, "message": "That hub already has a Hub Manager"}), 409
        updates["hub_id"] = new_hub["_id"]
        updates["hub_name"] = new_hub["name"]
        updates["district_name"] = new_hub.get("district_name")

    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    updates["updated_at"] = datetime.now(timezone.utc)

    hub_managers_col.update_one({"_id": oid}, {"$set": updates})
    updated = hub_managers_col.find_one({"_id": oid})
    return jsonify({"success": True, "hub_manager": serialize_hub_manager(updated)}), 200


@admin_hub_manager_bp.post("/<manager_id>/enable")
@admin_required
def enable_hub_manager(manager_id):
    try:
        oid = ObjectId(manager_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub manager id"}), 400
    result = hub_managers_col.update_one({"_id": oid}, {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Hub Manager not found"}), 404
    return jsonify({"success": True, "message": "Hub Manager account enabled"}), 200


@admin_hub_manager_bp.post("/<manager_id>/disable")
@admin_required
def disable_hub_manager(manager_id):
    try:
        oid = ObjectId(manager_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub manager id"}), 400
    result = hub_managers_col.update_one({"_id": oid}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Hub Manager not found"}), 404
    return jsonify({"success": True, "message": "Hub Manager account disabled"}), 200


@admin_hub_manager_bp.delete("/<manager_id>")
@admin_required
def delete_hub_manager(manager_id):
    try:
        oid = ObjectId(manager_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid hub manager id"}), 400
    result = hub_managers_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Hub Manager not found"}), 404
    return jsonify({"success": True}), 200
