"""
SYRA Fresh - Customer Auth Routes
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
PUT  /api/auth/me
GET  /api/auth/addresses
POST /api/auth/addresses
PUT  /api/auth/addresses/<address_id>
DELETE /api/auth/addresses/<address_id>
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from extensions import users_col, hash_password, verify_password
from models.user import new_user_doc, new_address_doc, serialize_user
from utils.validators import validate_registration, validate_address, is_valid_email
from utils.auth_utils import issue_token, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_registration(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    email = data["email"].strip().lower()
    if users_col.find_one({"email": email}):
        return jsonify({"success": False, "errors": {"email": "An account with this email already exists"}}), 409

    if data.get("phone") and users_col.find_one({"phone": data["phone"]}):
        return jsonify({"success": False, "errors": {"phone": "This phone number is already registered"}}), 409

    doc = new_user_doc(data["name"], email, hash_password(data["password"]), data.get("phone"))
    result = users_col.insert_one(doc)
    token = issue_token(result.inserted_id, role="customer")
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "token": token, "user": serialize_user(doc)}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    query = {"email": identifier} if is_valid_email(identifier) else {"phone": identifier}
    user = users_col.find_one(query)

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"success": False, "message": "Invalid email/phone or password"}), 401

    if not user.get("is_active", True):
        return jsonify({"success": False, "message": "This account has been disabled"}), 403

    token = issue_token(user["_id"], role="customer")
    return jsonify({"success": True, "token": token, "user": serialize_user(user)}), 200


@auth_bp.get("/me")
@login_required
def get_profile():
    return jsonify({"success": True, "user": serialize_user(request.current_user)}), 200


@auth_bp.put("/me")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    updates = {}
    if data.get("name"):
        updates["name"] = data["name"].strip()
    if data.get("phone"):
        updates["phone"] = data["phone"].strip()
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400

    updates["updated_at"] = datetime.now(timezone.utc)
    users_col.update_one({"_id": request.current_user["_id"]}, {"$set": updates})
    updated = users_col.find_one({"_id": request.current_user["_id"]})
    return jsonify({"success": True, "user": serialize_user(updated)}), 200


# ---------- Address management ----------

@auth_bp.get("/addresses")
@login_required
def list_addresses():
    return jsonify({"success": True, "addresses": request.current_user.get("addresses", [])}), 200


@auth_bp.post("/addresses")
@login_required
def add_address():
    data = request.get_json(silent=True) or {}
    errors = validate_address(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    is_default = bool(data.get("is_default")) or not request.current_user.get("addresses")
    addr = new_address_doc(
        data.get("label"), data["full_name"], data["phone"], data["line1"],
        data.get("line2"), data["city"], data["state"], data["pincode"], is_default,
    )

    if is_default:
        users_col.update_one(
            {"_id": request.current_user["_id"]},
            {"$set": {"addresses.$[].is_default": False}},
        )
    users_col.update_one({"_id": request.current_user["_id"]}, {"$push": {"addresses": addr}})
    return jsonify({"success": True, "address": addr}), 201


@auth_bp.put("/addresses/<address_id>")
@login_required
def update_address(address_id):
    data = request.get_json(silent=True) or {}
    errors = validate_address(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if data.get("is_default"):
        users_col.update_one(
            {"_id": request.current_user["_id"]},
            {"$set": {"addresses.$[].is_default": False}},
        )

    result = users_col.update_one(
        {"_id": request.current_user["_id"], "addresses._id": address_id},
        {"$set": {
            "addresses.$.label": data.get("label", "Home"),
            "addresses.$.full_name": data["full_name"],
            "addresses.$.phone": data["phone"],
            "addresses.$.line1": data["line1"],
            "addresses.$.line2": data.get("line2", ""),
            "addresses.$.city": data["city"],
            "addresses.$.state": data["state"],
            "addresses.$.pincode": data["pincode"],
            "addresses.$.is_default": bool(data.get("is_default", False)),
        }},
    )
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Address not found"}), 404
    return jsonify({"success": True}), 200


@auth_bp.delete("/addresses/<address_id>")
@login_required
def delete_address(address_id):
    users_col.update_one(
        {"_id": request.current_user["_id"]},
        {"$pull": {"addresses": {"_id": address_id}}},
    )
    return jsonify({"success": True}), 200
