"""
SYRA Fresh - Delivery Boy Authentication Routes
POST   /api/delivery/auth/register
POST   /api/delivery/auth/login
POST   /api/delivery/auth/forgot-password
POST   /api/delivery/auth/reset-password
POST   /api/delivery/auth/change-password
GET    /api/delivery/auth/me
PUT    /api/delivery/auth/me
POST   /api/delivery/auth/logout
"""
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.utils import secure_filename

from extensions import delivery_boys_col, hash_password, verify_password, hubs_col
from models.delivery_boy import new_delivery_boy_doc, serialize_delivery_boy
from utils.validators import validate_delivery_boy_registration, is_valid_email
from utils.auth_utils import issue_token, decode_token, delivery_boy_required
from utils.notification_service import NotificationService, EmailTemplates

delivery_auth_bp = Blueprint("delivery_auth", __name__, url_prefix="/api/delivery/auth")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file, subfolder="profile"):
    """Save uploaded file and return a URL the browser/admin panel can open directly.

    BUG FIX: this used to return a bare relative path like "aadhaar/xxx.jpg"
    with no leading slash and no "/static/uploads" prefix. The frontend then
    used that value directly as an <a href>, which the browser resolved
    relative to whatever admin page it was on (e.g. /admin/aadhaar/xxx.jpg)
    instead of the actual file location served by the
    `/static/uploads/<path:filename>` route in app.py -> guaranteed 404.
    Product image uploads in admin_routes.py already returned the correct
    "/static/uploads/{filename}" shape; this now matches that same pattern.
    """
    if not file or file.filename == "":
        return None
    
    if not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S_")
    filename = f"{timestamp}{filename}"
    
    subfolder_path = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(subfolder_path, exist_ok=True)
    
    filepath = os.path.join(subfolder_path, filename)
    file.save(filepath)
    
    return f"/static/uploads/{subfolder}/{filename}"


@delivery_auth_bp.post("/register")
def register():
    """
    Delivery boy registration with document upload.
    Status: pending_verification (requires admin approval)
    """
    data = request.form.to_dict()
    errors = validate_delivery_boy_registration(data)
    
    # Check file uploads
    if "aadhar_front" not in request.files:
        errors["aadhar_front"] = "Aadhar front image required"
    if "aadhar_back" not in request.files:
        errors["aadhar_back"] = "Aadhar back image required"

    # Phase 2: every delivery boy must belong to exactly one hub, chosen via
    # the district -> hub dropdowns on the registration form (populated from
    # GET /api/districts and GET /api/hubs?district_id=).
    hub = None
    hub_id_raw = data.get("hub_id")
    if not hub_id_raw:
        errors["hub_id"] = "Please select your district and hub"
    else:
        try:
            hub = hubs_col.find_one({"_id": ObjectId(hub_id_raw), "is_active": True})
        except InvalidId:
            hub = None
        if not hub:
            errors["hub_id"] = "Selected hub was not found. Please choose again."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    
    email = data["email"].strip().lower()
    mobile = data["mobile"].strip()
    
    if delivery_boys_col.find_one({"email": email}):
        return jsonify({"success": False, "errors": {"email": "Email already registered"}}), 409
    
    if delivery_boys_col.find_one({"mobile": mobile}):
        return jsonify({"success": False, "errors": {"mobile": "Mobile already registered"}}), 409
    
    # Process file uploads
    aadhar_front_url = save_upload_file(request.files.get("aadhar_front"), "aadhaar")
    aadhar_back_url = save_upload_file(request.files.get("aadhar_back"), "aadhaar")
    license_url = save_upload_file(request.files.get("license"), "license") if request.files.get("license") else None
    profile_photo_url = save_upload_file(request.files.get("profile_photo"), "profile") if request.files.get("profile_photo") else None
    
    if not aadhar_front_url or not aadhar_back_url:
        return jsonify({"success": False, "message": "Failed to upload Aadhar documents"}), 400
    
    # Prepare address data
    address_data = {
        "address": data.get("address"),
        "city": data.get("city"),
        "district": data.get("district"),
        "state": data.get("state"),
        "pincode": data.get("pincode"),
    }
    
    # Prepare document data
    document_data = {
        "alternate_mobile": data.get("alternate_mobile"),
        "aadhar_number": data.get("aadhar_number"),
        "aadhar_front_url": aadhar_front_url,
        "aadhar_back_url": aadhar_back_url,
        "license_number": data.get("license_number"),
        "license_url": license_url,
        "vehicle_type": data.get("vehicle_type"),
        "vehicle_number": data.get("vehicle_number"),
        "profile_photo_url": profile_photo_url,
        "emergency_contact": data.get("emergency_contact"),
        "delivery_area": data.get("delivery_area"),
        "available_time": data.get("available_time"),
        "upi_id": data.get("upi_id"),
        "bank_details": {
            "account_number": data.get("account_number"),
            "ifsc": data.get("ifsc"),
            "bank_name": data.get("bank_name"),
            "account_holder": data.get("account_holder"),
        } if data.get("account_number") else None,
    }
    
    # Create delivery boy doc
    doc = new_delivery_boy_doc(
        data["name"],
        email,
        mobile,
        hash_password(data["password"]),
        address_data,
        document_data,
        hub_id=hub["_id"],
        hub_name=hub["name"],
    )
    
    result = delivery_boys_col.insert_one(doc)
    
    # Send admin notification
    try:
        admin_data = {
            "delivery_boy_id": str(result.inserted_id),
            "delivery_boy_name": data["name"],
            "mobile": mobile,
            "city": data.get("city"),
        }
        NotificationService.notify_broadcast("admin_new_registration", admin_data, recipient_type="admin", channels=["in_app"])
    except Exception as e:
        current_app.logger.error(f"Failed to notify admin: {e}")
    
    return jsonify({
        "success": True,
        "message": "Registration successful. Awaiting admin verification.",
        "delivery_boy_id": str(result.inserted_id)
    }), 201


@delivery_auth_bp.post("/login")
def login():
    """Delivery boy login. Only approved delivery boys can login."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    if not identifier or not password:
        return jsonify({"success": False, "message": "Email/Mobile and password required"}), 400
    
    query = {"email": identifier} if is_valid_email(identifier) else {"mobile": identifier}
    delivery_boy = delivery_boys_col.find_one(query)
    
    if not delivery_boy or not verify_password(password, delivery_boy.get("password_hash", "")):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    
    if delivery_boy.get("status") != "approved":
        status_msg = {
            "pending_verification": "Your account is pending admin verification",
            "rejected": "Your registration was rejected",
            "suspended": "Your account has been suspended",
            "deactivated": "Your account has been deactivated",
        }
        return jsonify({"success": False, "message": status_msg.get(delivery_boy.get("status"), "Account not approved")}), 403
    
    token = issue_token(delivery_boy["_id"], role="delivery_boy")
    return jsonify({"success": True, "token": token, "delivery_boy": serialize_delivery_boy(delivery_boy)}), 200


@delivery_auth_bp.post("/forgot-password")
def forgot_password():
    """Request password reset link."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or "").strip().lower()
    
    if not identifier:
        return jsonify({"success": False, "message": "Email required"}), 400
    
    query = {"email": identifier} if is_valid_email(identifier) else {"mobile": identifier}
    delivery_boy = delivery_boys_col.find_one(query)
    
    if not delivery_boy:
        return jsonify({"success": True, "message": "If account exists, reset link has been sent"}), 200
    
    # Real single-purpose, short-lived reset token (was previously a hardcoded "xyz"
    # placeholder that reset-password didn't even check). Reuses the app's existing
    # JWT signing/verification instead of introducing a new storage mechanism.
    from datetime import timedelta
    reset_token = issue_token(delivery_boy["_id"], role="delivery_password_reset", expires=timedelta(minutes=30))
    try:
        reset_link = f"https://syra.app/delivery/reset-password?token={reset_token}"
        email_data = EmailTemplates.password_reset(delivery_boy.get("name"), reset_link)
        NotificationService.send_email(delivery_boy.get("email"), email_data["subject"], email_data["body"])
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
    
    return jsonify({"success": True, "message": "If account exists, reset link has been sent"}), 200


@delivery_auth_bp.post("/reset-password")
def reset_password():
    """Reset password using the token issued by /forgot-password."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    if not all([token, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields required"}), 400
    
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400
    
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400
    
    payload = decode_token(token)
    if not payload or payload.get("role") != "delivery_password_reset":
        return jsonify({"success": False, "message": "Reset link is invalid or has expired"}), 400
    
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(payload["sub"])})
    except InvalidId:
        delivery_boy = None
    if not delivery_boy:
        return jsonify({"success": False, "message": "Account not found"}), 404
    
    delivery_boys_col.update_one(
        {"_id": delivery_boy["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}}
    )
    
    return jsonify({"success": True, "message": "Password reset successful"}), 200


@delivery_auth_bp.get("/me")
@delivery_boy_required
def get_profile():
    """Get current delivery boy profile."""
    return jsonify({"success": True, "delivery_boy": serialize_delivery_boy(request.current_delivery_boy)}), 200


@delivery_auth_bp.put("/me")
@delivery_boy_required
def update_profile():
    """Update delivery boy profile."""
    data = request.get_json(silent=True) or {}
    updates = {}
    
    if data.get("name"):
        updates["name"] = data["name"].strip()
    
    if data.get("alternate_mobile"):
        updates["alternate_mobile"] = data["alternate_mobile"].strip()
    
    if data.get("emergency_contact"):
        updates["emergency_contact"] = data["emergency_contact"].strip()
    
    if data.get("available_time"):
        updates["available_time"] = data["available_time"]
    
    if data.get("upi_id"):
        updates["upi_id"] = data["upi_id"].strip()
    
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    
    updates["updated_at"] = datetime.now(timezone.utc)
    delivery_boys_col.update_one({"_id": request.current_delivery_boy["_id"]}, {"$set": updates})
    updated = delivery_boys_col.find_one({"_id": request.current_delivery_boy["_id"]})
    
    return jsonify({"success": True, "delivery_boy": serialize_delivery_boy(updated)}), 200


@delivery_auth_bp.post("/change-password")
@delivery_boy_required
def change_password():
    """Change password for the logged-in delivery boy.

    NOTE: frontend/delivery/settings.html already called
    POST /api/delivery/auth/change-password, but this endpoint never existed
    on the backend, so every password change from Settings failed.
    """
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields required"}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    delivery_boy = request.current_delivery_boy
    if not verify_password(current_password, delivery_boy.get("password_hash", "")):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400

    delivery_boys_col.update_one(
        {"_id": delivery_boy["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}}
    )

    return jsonify({"success": True, "message": "Password updated successfully"}), 200


@delivery_auth_bp.post("/logout")
@delivery_boy_required
def logout():
    """Logout delivery boy (token invalidation on client side)."""
    return jsonify({"success": True, "message": "Logged out successfully"}), 200
