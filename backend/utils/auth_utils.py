"""
SYRA Fresh - Auth Utilities
JWT issuing/verification and decorators to protect customer and admin routes.
"""
from functools import wraps
from datetime import datetime, timezone
import jwt
from flask import request, jsonify, current_app
from bson import ObjectId
from bson.errors import InvalidId
from extensions import users_col, admins_col, delivery_boys_col, hub_managers_col


def issue_token(user_id, role="customer", expires=None):
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + (expires or current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def login_required(f):
    """Protect customer-facing routes. Attaches request.current_user (dict)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        payload = decode_token(token)
        if not payload or payload.get("role") != "customer":
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401
        try:
            user = users_col.find_one({"_id": ObjectId(payload["sub"])})
        except InvalidId:
            user = None
        if not user or not user.get("is_active", True):
            return jsonify({"success": False, "message": "Account not found or disabled"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Protect admin panel routes. Attaches request.current_admin (dict)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"success": False, "message": "Admin authentication required"}), 401
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            return jsonify({"success": False, "message": "Invalid or expired admin token"}), 401
        try:
            admin = admins_col.find_one({"_id": ObjectId(payload["sub"])})
        except InvalidId:
            admin = None
        if not admin:
            return jsonify({"success": False, "message": "Admin not found"}), 401
        request.current_admin = admin
        return f(*args, **kwargs)
    return wrapper


def delivery_boy_required(f):
    """Protect delivery boy routes. Attaches request.current_delivery_boy (dict)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"success": False, "message": "Delivery boy authentication required"}), 401
        payload = decode_token(token)
        if not payload or payload.get("role") != "delivery_boy":
            return jsonify({"success": False, "message": "Invalid or expired delivery boy token"}), 401
        try:
            delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(payload["sub"])})
        except InvalidId:
            delivery_boy = None
        if not delivery_boy:
            return jsonify({"success": False, "message": "Delivery boy not found"}), 401
        if delivery_boy.get("status") != "approved":
            return jsonify({"success": False, "message": "Your account is not approved or has been suspended"}), 403
        request.current_delivery_boy = delivery_boy
        return f(*args, **kwargs)
    return wrapper


def hub_manager_required(f):
    """Protect Hub Manager panel routes. Attaches request.current_hub_manager (dict).

    RBAC: a hub manager only ever sees their own hub's data. Every route that
    uses this decorator must filter its MongoDB queries by
    request.current_hub_manager["hub_id"] - this decorator only proves *who*
    is calling, not what they're allowed to see; each route is still
    responsible for scoping its own queries.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"success": False, "message": "Hub Manager authentication required"}), 401
        payload = decode_token(token)
        if not payload or payload.get("role") != "hub_manager":
            return jsonify({"success": False, "message": "Invalid or expired Hub Manager token"}), 401
        try:
            hub_manager = hub_managers_col.find_one({"_id": ObjectId(payload["sub"])})
        except InvalidId:
            hub_manager = None
        if not hub_manager:
            return jsonify({"success": False, "message": "Hub Manager not found"}), 401
        if not hub_manager.get("is_active", True):
            return jsonify({"success": False, "message": "Your account has been disabled"}), 403
        request.current_hub_manager = hub_manager
        return f(*args, **kwargs)
    return wrapper
