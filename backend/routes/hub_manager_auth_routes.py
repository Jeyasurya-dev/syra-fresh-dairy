"""
SYRA Fresh - Hub Manager Auth Routes (Phase 2)
POST /api/hub-manager/auth/login
GET  /api/hub-manager/auth/me
POST /api/hub-manager/auth/change-password
POST /api/hub-manager/auth/logout

No self-registration: accounts are created by the Super Admin
(see admin_hub_manager_routes.py).
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from extensions import hub_managers_col, hash_password, verify_password
from models.hub_manager import serialize_hub_manager
from utils.auth_utils import issue_token, hub_manager_required

hub_manager_auth_bp = Blueprint("hub_manager_auth", __name__, url_prefix="/api/hub-manager/auth")


@hub_manager_auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    manager = hub_managers_col.find_one({"email": email})
    if not manager or not verify_password(password, manager.get("password_hash", "")):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    if not manager.get("is_active", True):
        return jsonify({"success": False, "message": "Your account has been disabled. Contact the Super Admin."}), 403

    token = issue_token(manager["_id"], role="hub_manager", expires=current_app.config["JWT_ADMIN_TOKEN_EXPIRES"])
    return jsonify({"success": True, "token": token, "hub_manager": serialize_hub_manager(manager)}), 200


@hub_manager_auth_bp.get("/me")
@hub_manager_required
def get_profile():
    return jsonify({"success": True, "hub_manager": serialize_hub_manager(request.current_hub_manager)}), 200


@hub_manager_auth_bp.put("/me")
@hub_manager_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400

    hub_managers_col.update_one(
        {"_id": request.current_hub_manager["_id"]},
        {"$set": {"name": name, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = hub_managers_col.find_one({"_id": request.current_hub_manager["_id"]})
    return jsonify({"success": True, "hub_manager": serialize_hub_manager(updated)}), 200


@hub_manager_auth_bp.post("/change-password")
@hub_manager_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields are required"}), 400
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters"}), 400

    manager = request.current_hub_manager
    if not verify_password(current_password, manager.get("password_hash", "")):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400

    hub_managers_col.update_one(
        {"_id": manager["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    return jsonify({"success": True, "message": "Password updated successfully"}), 200


@hub_manager_auth_bp.post("/logout")
@hub_manager_required
def logout():
    return jsonify({"success": True, "message": "Logged out successfully"}), 200
