"""
SYRA Fresh - Notifications Routes
GET    /api/notifications
GET    /api/notifications/<notification_id>
PUT    /api/notifications/<notification_id>/read
POST   /api/notifications/mark-all-read
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import notifications_col
from utils.auth_utils import login_required, delivery_boy_required, admin_required

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@login_required
def get_notifications():
    """Get notifications for current user (customer)."""
    user_id = request.current_user["_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    skip = (page - 1) * limit
    
    query = {
        "recipient_id": user_id,
        "recipient_type": "customer"
    }
    
    if unread_only:
        query["read"] = False
    
    notifications = list(notifications_col.find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = notifications_col.count_documents(query)
    unread_count = notifications_col.count_documents({
        "recipient_id": user_id,
        "recipient_type": "customer",
        "read": False
    })
    
    return jsonify({
        "success": True,
        "notifications": [serialize_notification(n) for n in notifications],
        "unread_count": unread_count,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        }
    }), 200


@notifications_bp.get("/delivery")
@delivery_boy_required
def get_delivery_notifications():
    """Get notifications for delivery boy.

    NOTE: previously `@notifications_bp.get("", subdomain="delivery")`, which was
    unreachable for the same reason as the admin route above — no SERVER_NAME is
    configured, so subdomain routing never activates. Moved to /api/notifications/delivery.
    """
    delivery_boy_id = request.current_delivery_boy["_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    skip = (page - 1) * limit
    
    query = {
        "recipient_id": delivery_boy_id,
        "recipient_type": "delivery_boy"
    }
    
    if unread_only:
        query["read"] = False
    
    notifications = list(notifications_col.find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = notifications_col.count_documents(query)
    unread_count = notifications_col.count_documents({
        "recipient_id": delivery_boy_id,
        "recipient_type": "delivery_boy",
        "read": False
    })
    
    return jsonify({
        "success": True,
        "notifications": [serialize_notification(n) for n in notifications],
        "unread_count": unread_count,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        }
    }), 200


@notifications_bp.get("/admin")
@admin_required
def get_admin_notifications():
    """Get notifications for admin.

    NOTE: previously this was registered as `@notifications_bp.get("", subdomain="admin")`,
    which is unreachable — this Flask app never sets app.config['SERVER_NAME'], so
    subdomain-based routing is not active anywhere in the project (every other admin/delivery
    endpoint uses a path prefix, e.g. /api/admin/..., /api/delivery/...). Moved to a real
    path (/api/notifications/admin) so it actually matches requests.
    """
    admin_id = request.current_admin["_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    skip = (page - 1) * limit
    
    query = {
        "recipient_id": admin_id,
        "recipient_type": "admin"
    }
    
    if unread_only:
        query["read"] = False
    
    notifications = list(notifications_col.find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = notifications_col.count_documents(query)
    unread_count = notifications_col.count_documents({
        "recipient_id": admin_id,
        "recipient_type": "admin",
        "read": False
    })
    
    return jsonify({
        "success": True,
        "notifications": [serialize_notification(n) for n in notifications],
        "unread_count": unread_count,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        }
    }), 200


@notifications_bp.put("/<notification_id>/read")
def mark_as_read(notification_id):
    """Mark notification as read.

    SECURITY FIX: this endpoint previously had no auth decorator at all —
    any unauthenticated request could mark any notification (by ID) as read
    for any customer/admin/delivery boy. It now requires a valid token for
    one of the three roles and verifies the caller owns the notification
    before updating it.
    """
    from utils.auth_utils import _get_bearer_token, decode_token

    token = _get_bearer_token()
    payload = decode_token(token) if token else None
    if not payload:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    role_to_recipient_type = {"customer": "customer", "admin": "admin", "delivery_boy": "delivery_boy"}
    recipient_type = role_to_recipient_type.get(payload.get("role"))
    if not recipient_type:
        return jsonify({"success": False, "message": "Invalid token"}), 401

    try:
        notification = notifications_col.find_one({"_id": ObjectId(notification_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid notification ID"}), 400
    
    if not notification:
        return jsonify({"success": False, "message": "Notification not found"}), 404

    if str(notification.get("recipient_id")) != str(payload.get("sub")) or notification.get("recipient_type") != recipient_type:
        return jsonify({"success": False, "message": "Not authorized to update this notification"}), 403
    
    notifications_col.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {
            "read": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return jsonify({"success": True, "message": "Marked as read"}), 200


@notifications_bp.delete("/<notification_id>")
def delete_notification(notification_id):
    """Delete a single notification for the calling customer/admin/delivery boy.

    MISSING FEATURE: frontend/pages/notifications.html already rendered a
    "Delete" button on every notification card, but there was no matching
    backend route at all - clicking it just showed a "not available yet"
    toast. Uses the same auth + ownership check as mark_as_read above so a
    caller can only delete their own notifications.
    """
    from utils.auth_utils import _get_bearer_token, decode_token

    token = _get_bearer_token()
    payload = decode_token(token) if token else None
    if not payload:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    role_to_recipient_type = {"customer": "customer", "admin": "admin", "delivery_boy": "delivery_boy"}
    recipient_type = role_to_recipient_type.get(payload.get("role"))
    if not recipient_type:
        return jsonify({"success": False, "message": "Invalid token"}), 401

    try:
        notification = notifications_col.find_one({"_id": ObjectId(notification_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid notification ID"}), 400

    if not notification:
        return jsonify({"success": False, "message": "Notification not found"}), 404

    if str(notification.get("recipient_id")) != str(payload.get("sub")) or notification.get("recipient_type") != recipient_type:
        return jsonify({"success": False, "message": "Not authorized to delete this notification"}), 403

    notifications_col.delete_one({"_id": ObjectId(notification_id)})
    return jsonify({"success": True, "message": "Notification deleted"}), 200


@notifications_bp.post("/mark-all-read")
def mark_all_as_read():
    """Mark all notifications as read for whichever role the token belongs to.

    NOTE: previously `@login_required` (customer-only), so the admin panel's
    "Mark All as Read" button always failed with 401 for admin tokens. Now
    accepts customer, admin, or delivery boy tokens and scopes the update to
    that recipient.
    """
    from utils.auth_utils import _get_bearer_token, decode_token

    token = _get_bearer_token()
    payload = decode_token(token) if token else None
    if not payload:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    role_to_recipient_type = {"customer": "customer", "admin": "admin", "delivery_boy": "delivery_boy"}
    recipient_type = role_to_recipient_type.get(payload.get("role"))
    if not recipient_type:
        return jsonify({"success": False, "message": "Invalid token"}), 401

    notifications_col.update_many(
        {
            "recipient_id": ObjectId(payload["sub"]),
            "recipient_type": recipient_type,
            "read": False
        },
        {"$set": {
            "read": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return jsonify({"success": True, "message": "All notifications marked as read"}), 200


def serialize_notification(doc):
    """Serialize notification for API response."""
    if not doc:
        return None
    
    return {
        "id": str(doc["_id"]),
        "type": doc.get("notification_type"),
        "title": doc.get("title"),
        "data": doc.get("data"),
        "channels": doc.get("channels", []),
        "read": doc.get("read", False),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
