"""
SYRA Fresh - Admin Delivery Boy Management Routes
GET    /api/admin/delivery-boys
GET    /api/admin/delivery-boys/<delivery_boy_id>
PUT    /api/admin/delivery-boys/<delivery_boy_id>
DELETE /api/admin/delivery-boys/<delivery_boy_id>
POST   /api/admin/delivery-boys/<delivery_boy_id>/approve
POST   /api/admin/delivery-boys/<delivery_boy_id>/reject
POST   /api/admin/delivery-boys/<delivery_boy_id>/suspend
POST   /api/admin/delivery-boys/<delivery_boy_id>/activate
POST   /api/admin/delivery-boys/<delivery_boy_id>/assign-order
GET    /api/admin/delivery-assignments
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from bson.errors import InvalidId

from extensions import delivery_boys_col, delivery_assignments_col, orders_col, hubs_col
from utils.auth_utils import admin_required
from models.delivery_boy import new_delivery_assignment_doc, serialize_delivery_boy_admin
from utils.notification_service import NotificationService

admin_delivery_bp = Blueprint("admin_delivery", __name__, url_prefix="/api/admin/delivery-boys")


@admin_delivery_bp.get("")
@admin_required
def list_delivery_boys():
    """List all delivery boys with filters and pagination."""
    admin = request.current_admin
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")  # approved, pending_verification, rejected, suspended, deactivated
    search = request.args.get("search", "").strip()
    hub_id = request.args.get("hub_id")  # Phase 2: filter delivery boys by hub

    skip = (page - 1) * limit
    
    query = {}
    if status:
        query["status"] = status
    if hub_id:
        try:
            query["hub_id"] = ObjectId(hub_id)
        except InvalidId:
            return jsonify({"success": False, "message": "Invalid hub id"}), 400
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"mobile": {"$regex": search, "$options": "i"}}
        ]
    
    delivery_boys = list(delivery_boys_col.find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = delivery_boys_col.count_documents(query)
    
    return jsonify({
        "success": True,
        "delivery_boys": [serialize_delivery_boy_admin(db) for db in delivery_boys],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }), 200


@admin_delivery_bp.get("/<delivery_boy_id>")
@admin_required
def get_delivery_boy_detail(delivery_boy_id):
    """Get detailed information about a delivery boy."""
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    # Get assignment stats
    total_assignments = delivery_assignments_col.count_documents({"delivery_boy_id": ObjectId(delivery_boy_id)})
    completed_assignments = delivery_assignments_col.count_documents({
        "delivery_boy_id": ObjectId(delivery_boy_id),
        "status": "delivered"
    })
    
    return jsonify({
        "success": True,
        "delivery_boy": serialize_delivery_boy_admin(delivery_boy),
        "stats": {
            "total_assignments": total_assignments,
            "completed_assignments": completed_assignments,
            "success_rate": f"{(completed_assignments / total_assignments * 100) if total_assignments > 0 else 0:.2f}%"
        }
    }), 200


@admin_delivery_bp.put("/<delivery_boy_id>")
@admin_required
def update_delivery_boy(delivery_boy_id):
    """Update delivery boy details."""
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    data = request.get_json(silent=True) or {}
    updates = {}
    
    # Allow only certain fields to be updated
    updateable_fields = ["delivery_area", "available_time", "vehicle_number", "vehicle_type"]
    for field in updateable_fields:
        if field in data:
            updates[field] = data[field]
    
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    
    updates["updated_at"] = datetime.now(timezone.utc)
    delivery_boys_col.update_one({"_id": ObjectId(delivery_boy_id)}, {"$set": updates})
    updated = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    
    return jsonify({"success": True, "delivery_boy": serialize_delivery_boy_admin(updated)}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/transfer")
@admin_required
def transfer_delivery_boy(delivery_boy_id):
    """Phase 2: transfer a delivery boy to a different hub.

    Super Admin only - this is exactly the "Transfer Delivery Boys" feature
    from the architecture brief. Hub Managers cannot transfer delivery boys
    between hubs (they can only manage the ones already in their own hub).
    """
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404

    data = request.get_json(silent=True) or {}
    hub_id = data.get("hub_id")
    if not hub_id:
        return jsonify({"success": False, "message": "hub_id is required"}), 400

    try:
        hub = hubs_col.find_one({"_id": ObjectId(hub_id)})
    except InvalidId:
        hub = None
    if not hub:
        return jsonify({"success": False, "message": "Hub not found"}), 404

    delivery_boys_col.update_one(
        {"_id": delivery_boy["_id"]},
        {"$set": {"hub_id": hub["_id"], "hub_name": hub["name"], "updated_at": datetime.now(timezone.utc)}},
    )
    updated = delivery_boys_col.find_one({"_id": delivery_boy["_id"]})
    return jsonify({"success": True, "delivery_boy": serialize_delivery_boy_admin(updated)}), 200


@admin_delivery_bp.delete("/<delivery_boy_id>")
@admin_required
def delete_delivery_boy(delivery_boy_id):
    """Soft delete a delivery boy (deactivate)."""
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    delivery_boys_col.update_one(
        {"_id": ObjectId(delivery_boy_id)},
        {"$set": {
            "status": "deactivated",
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return jsonify({"success": True, "message": "Delivery boy deactivated"}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/approve")
@admin_required
def approve_delivery_boy(delivery_boy_id):
    """Approve a pending delivery boy registration."""
    admin = request.current_admin
    
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    if delivery_boy.get("status") != "pending_verification":
        return jsonify({"success": False, "message": "Only pending registrations can be approved"}), 400
    
    now = datetime.now(timezone.utc)
    delivery_boys_col.update_one(
        {"_id": ObjectId(delivery_boy_id)},
        {"$set": {
            "status": "approved",
            "verified_by": admin["_id"],
            "verified_at": now,
            "updated_at": now
        }}
    )
    
    # Notify delivery boy
    try:
        NotificationService.notify_delivery_boy(
            ObjectId(delivery_boy_id),
            "delivery_approved",
            {
                "delivery_boy_name": delivery_boy.get("name"),
                "message": "Your registration has been approved!"
            },
            channels=["in_app"]
        )
    except Exception as e:
        current_app.logger.error(f"Failed to notify delivery boy: {e}")
    
    return jsonify({"success": True, "message": "Delivery boy approved"}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/reject")
@admin_required
def reject_delivery_boy(delivery_boy_id):
    """Reject a pending delivery boy registration."""
    admin = request.current_admin
    data = request.get_json(silent=True) or {}
    rejection_reason = data.get("reason", "Registration rejected")
    
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    now = datetime.now(timezone.utc)
    delivery_boys_col.update_one(
        {"_id": ObjectId(delivery_boy_id)},
        {"$set": {
            "status": "rejected",
            "verification_notes": rejection_reason,
            "verified_by": admin["_id"],
            "verified_at": now,
            "updated_at": now
        }}
    )
    
    return jsonify({"success": True, "message": "Delivery boy registration rejected"}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/suspend")
@admin_required
def suspend_delivery_boy(delivery_boy_id):
    """Suspend a delivery boy temporarily."""
    admin = request.current_admin
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Suspended")
    
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    now = datetime.now(timezone.utc)
    delivery_boys_col.update_one(
        {"_id": ObjectId(delivery_boy_id)},
        {"$set": {
            "status": "suspended",
            "verification_notes": reason,
            "is_online": False,
            "updated_at": now
        }}
    )
    
    return jsonify({"success": True, "message": "Delivery boy suspended"}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/activate")
@admin_required
def activate_delivery_boy(delivery_boy_id):
    """Reactivate a suspended or rejected delivery boy."""
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    delivery_boys_col.update_one(
        {"_id": ObjectId(delivery_boy_id)},
        {"$set": {
            "status": "approved",
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return jsonify({"success": True, "message": "Delivery boy activated"}), 200


@admin_delivery_bp.post("/<delivery_boy_id>/assign-order")
@admin_required
def assign_order_to_delivery_boy(delivery_boy_id):
    """Assign an order to a delivery boy."""
    admin = request.current_admin
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    
    if not order_id:
        return jsonify({"success": False, "message": "Order ID required"}), 400
    
    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    
    if not delivery_boy:
        return jsonify({"success": False, "message": "Delivery boy not found"}), 404
    
    if delivery_boy.get("status") != "approved":
        return jsonify({"success": False, "message": "Delivery boy is not approved"}), 400
    
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid order ID"}), 400
    
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    
    # Check if already assigned
    existing = delivery_assignments_col.find_one({"order_id": order_id})
    if existing:
        return jsonify({"success": False, "message": "Order already assigned"}), 400
    
    # Create assignment
    assignment_doc = new_delivery_assignment_doc(
        order_id,
        ObjectId(delivery_boy_id),
        delivery_boy.get("name"),
        admin["_id"]
    )
    
    result = delivery_assignments_col.insert_one(assignment_doc)
    
    # Update order with delivery boy info
    now = datetime.now(timezone.utc)
    orders_col.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "delivery_boy_id": ObjectId(delivery_boy_id),
            "delivery_boy_name": delivery_boy.get("name"),
            "assigned_at": now,
            "assigned_by": admin["_id"],
            "status": "Packed",
            "updated_at": now
        },
        "$push": {
            "status_history": {
                "status": "Packed",
                "at": now
            }
        }}
    )
    
    # Notify delivery boy
    try:
        NotificationService.notify_delivery_boy(
            ObjectId(delivery_boy_id),
            "delivery_new_assignment",
            {
                "order_number": order.get("order_number"),
                "customer_name": order.get("customer_name"),
            },
            channels=["in_app"]
        )
    except Exception as e:
        current_app.logger.error(f"Failed to notify delivery boy: {e}")
    
    # Notify customer
    try:
        NotificationService.notify_customer(
            order["user_id"],
            "delivery_boy_assigned",
            {
                "order_number": order.get("order_number"),
                "delivery_boy_name": delivery_boy.get("name"),
                "delivery_boy_phone": delivery_boy.get("mobile"),
            },
            channels=["in_app"]
        )
    except Exception as e:
        current_app.logger.error(f"Failed to notify customer: {e}")
    
    return jsonify({
        "success": True,
        "message": "Order assigned to delivery boy",
        "assignment_id": str(result.inserted_id)
    }), 201


@admin_delivery_bp.get("/assignments")
@admin_required
def list_delivery_assignments():
    """List all delivery assignments with filters."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")
    
    skip = (page - 1) * limit
    
    query = {}
    if status:
        query["status"] = status
    
    assignments = list(delivery_assignments_col.find(query).sort("assigned_at", -1).skip(skip).limit(limit))
    total = delivery_assignments_col.count_documents(query)
    
    enriched = []
    for assignment in assignments:
        try:
            order = orders_col.find_one({"_id": ObjectId(assignment["order_id"])})
            delivery_boy = delivery_boys_col.find_one({"_id": assignment["delivery_boy_id"]})
            
            enriched.append({
                "assignment_id": str(assignment["_id"]),
                "order_id": str(assignment["order_id"]),
                "order_number": order.get("order_number") if order else None,
                "delivery_boy_name": delivery_boy.get("name") if delivery_boy else None,
                "delivery_boy_phone": delivery_boy.get("mobile") if delivery_boy else None,
                "status": assignment.get("status"),
                "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
            })
        except:
            pass
    
    return jsonify({
        "success": True,
        "assignments": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }), 200
