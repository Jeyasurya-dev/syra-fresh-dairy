"""
SYRA Fresh - Delivery Boy Operations Routes
GET    /api/delivery/dashboard
GET    /api/delivery/assignments
GET    /api/delivery/assignments/<assignment_id>
PUT    /api/delivery/assignments/<assignment_id>/status
POST   /api/delivery/assignments/<assignment_id>/location
GET    /api/delivery/history
GET    /api/delivery/earnings
POST   /api/delivery/toggle-online
"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app, send_file
from bson import ObjectId
from bson.errors import InvalidId

from extensions import (
    delivery_boys_col, delivery_assignments_col, orders_col, 
    delivery_locations_col, users_col, salary_transactions_col
)
from models.salary import serialize_salary_transaction
from utils.pdf_generator import generate_salary_slip_pdf
from utils.auth_utils import delivery_boy_required
from utils.notification_service import NotificationService

delivery_bp = Blueprint("delivery", __name__, url_prefix="/api/delivery")


@delivery_bp.get("/dashboard")
@delivery_boy_required
def get_dashboard():
    """Get delivery boy dashboard with summary stats."""
    delivery_boy = request.current_delivery_boy
    delivery_boy_id = delivery_boy["_id"]
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Count assignments by status
    total_assigned = delivery_assignments_col.count_documents({
        "delivery_boy_id": delivery_boy_id,
        "status": "assigned"
    })
    
    out_for_delivery = delivery_assignments_col.count_documents({
        "delivery_boy_id": delivery_boy_id,
        "status": "out_for_delivery"
    })
    
    delivered_today = delivery_assignments_col.count_documents({
        "delivery_boy_id": delivery_boy_id,
        "status": "delivered",
        "delivered_at": {"$gte": today_start, "$lt": today_end}
    })
    
    # COD collection
    # BUG FIX: this previously ran the exact same aggregation twice (once
    # into an unused variable, then again inside the ternary just to check
    # truthiness) - wasteful and confusing. One query, used once.
    cod_pending = list(delivery_assignments_col.aggregate([
        {
            "$match": {
                "delivery_boy_id": delivery_boy_id,
                "status": "delivered",
                "cod_submitted": False
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$cod_collected"}
            }
        }
    ]))
    cod_total = cod_pending[0]["total"] if cod_pending else 0
    
    return jsonify({
        "success": True,
        "dashboard": {
            "assigned_orders": total_assigned,
            "out_for_delivery": out_for_delivery,
            "delivered_today": delivered_today,
            "cod_pending": cod_total,
            "is_online": delivery_boy.get("is_online", False),
            "total_deliveries": delivery_boy.get("total_deliveries", 0),
            "successful_deliveries": delivery_boy.get("successful_deliveries", 0),
            "failed_deliveries": delivery_boy.get("failed_deliveries", 0),
            "rating": delivery_boy.get("rating", 5.0),
            "total_earnings": delivery_boy.get("total_earnings", 0.0)
        }
    }), 200


@delivery_bp.get("/assignments")
@delivery_boy_required
def get_assignments():
    """Get all assignments for delivery boy with pagination."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")  # Optional filter
    
    skip = (page - 1) * limit
    
    query = {"delivery_boy_id": delivery_boy_id}
    if status:
        query["status"] = status
    
    assignments = list(delivery_assignments_col.find(query).sort("assigned_at", -1).skip(skip).limit(limit))
    total = delivery_assignments_col.count_documents(query)
    
    # Enrich with order details
    enriched_assignments = []
    for assignment in assignments:
        try:
            order = orders_col.find_one({"_id": ObjectId(assignment["order_id"])})
            customer = users_col.find_one({"_id": ObjectId(order["user_id"])}) if order else None
            
            enriched_assignments.append({
                "assignment_id": str(assignment["_id"]),
                "order_id": str(assignment["order_id"]),
                "order_number": order.get("order_number") if order else None,
                "customer_name": customer.get("name") if customer else None,
                "customer_phone": customer.get("phone") if customer else None,
                "delivery_address": order.get("address") if order else None,
                "status": assignment.get("status"),
                "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
                "cod_collected": assignment.get("cod_collected", 0.0),
                "estimated_delivery_time": assignment.get("estimated_delivery_time"),
            })
        except Exception as e:
            current_app.logger.error(f"Error enriching assignment: {e}")
            continue
    
    return jsonify({
        "success": True,
        "assignments": enriched_assignments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }), 200


@delivery_bp.get("/assignments/<assignment_id>")
@delivery_boy_required
def get_assignment_detail(assignment_id):
    """Get detailed information about a specific assignment."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    
    try:
        assignment = delivery_assignments_col.find_one({
            "_id": ObjectId(assignment_id),
            "delivery_boy_id": delivery_boy_id
        })
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid assignment ID"}), 400
    
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404
    
    try:
        order = orders_col.find_one({"_id": ObjectId(assignment["order_id"])})
        customer = users_col.find_one({"_id": ObjectId(order["user_id"])}) if order else None
        
        return jsonify({
            "success": True,
            "assignment": {
                "assignment_id": str(assignment["_id"]),
                "order_id": str(assignment["order_id"]),
                "order_number": order.get("order_number") if order else None,
                "customer": {
                    "name": customer.get("name") if customer else None,
                    "phone": customer.get("phone") if customer else None,
                    "email": customer.get("email") if customer else None,
                },
                "delivery_address": order.get("address") if order else None,
                "order_items": order.get("items", []) if order else [],
                "status": assignment.get("status"),
                "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
                "picked_up_at": assignment.get("picked_up_at").isoformat() if assignment.get("picked_up_at") else None,
                "out_for_delivery_at": assignment.get("out_for_delivery_at").isoformat() if assignment.get("out_for_delivery_at") else None,
                "delivered_at": assignment.get("delivered_at").isoformat() if assignment.get("delivered_at") else None,
                "cod_collected": assignment.get("cod_collected", 0.0),
                "delivery_notes": assignment.get("delivery_notes"),
                "estimated_delivery_time": assignment.get("estimated_delivery_time"),
                "payment_method": order.get("payment_method") if order else None,
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching assignment details: {e}")
        return jsonify({"success": False, "message": "Error fetching details"}), 500


@delivery_bp.put("/assignments/<assignment_id>/status")
@delivery_boy_required
def update_assignment_status(assignment_id):
    """Update delivery assignment status."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    
    valid_statuses = ["picked_up", "out_for_delivery", "delivered", "failed"]
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of: {valid_statuses}"}), 400
    
    try:
        assignment = delivery_assignments_col.find_one({
            "_id": ObjectId(assignment_id),
            "delivery_boy_id": delivery_boy_id
        })
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid assignment ID"}), 400
    
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404
    
    updates = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Update timestamp based on status
    now = datetime.now(timezone.utc)
    if new_status == "picked_up":
        updates["picked_up_at"] = now
    elif new_status == "out_for_delivery":
        updates["out_for_delivery_at"] = now
    elif new_status == "delivered":
        updates["delivered_at"] = now
        # Update order status to "Delivered"
        orders_col.update_one({"_id": ObjectId(assignment["order_id"])}, {
            "$set": {
                "status": "Delivered",
                "updated_at": now,
            },
            "$push": {
                "status_history": {
                    "status": "Delivered",
                    "at": now
                }
            }
        })
        # Update delivery boy stats
        delivery_boys_col.update_one(
            {"_id": delivery_boy_id},
            {
                "$inc": {"successful_deliveries": 1, "total_deliveries": 1},
                "$set": {"updated_at": now}
            }
        )
        # Notify customer
        try:
            order = orders_col.find_one({"_id": ObjectId(assignment["order_id"])})
            customer = users_col.find_one({"_id": ObjectId(order["user_id"])})
            NotificationService.notify_customer(
                order["user_id"],
                "order_delivered",
                {
                    "order_number": order.get("order_number"),
                    "delivery_boy_name": request.current_delivery_boy.get("name"),
                },
                channels=["in_app", "email"]
            )
        except Exception as e:
            current_app.logger.error(f"Failed to notify customer: {e}")
    
    elif new_status == "failed":
        failure_reason = data.get("failure_reason", "Unknown reason")
        updates["failure_reason"] = failure_reason
        # Update delivery boy stats
        delivery_boys_col.update_one(
            {"_id": delivery_boy_id},
            {
                "$inc": {"failed_deliveries": 1, "total_deliveries": 1},
                "$set": {"updated_at": now}
            }
        )
        # Notify admin
        try:
            order = orders_col.find_one({"_id": ObjectId(assignment["order_id"])})
            NotificationService.notify_broadcast(
                "admin_failed_delivery",
                {
                    "order_number": order.get("order_number") if order else None,
                    "delivery_boy_name": request.current_delivery_boy.get("name"),
                    "failure_reason": failure_reason,
                },
                recipient_type="admin",
                channels=["in_app"]
            )
        except Exception as e:
            current_app.logger.error(f"Failed to notify admin: {e}")
    
    delivery_assignments_col.update_one({"_id": ObjectId(assignment_id)}, {"$set": updates})
    updated = delivery_assignments_col.find_one({"_id": ObjectId(assignment_id)})
    
    return jsonify({
        "success": True,
        "message": f"Status updated to {new_status}",
        "assignment_id": assignment_id
    }), 200


@delivery_bp.post("/assignments/<assignment_id>/location")
@delivery_boy_required
def update_location(assignment_id):
    """Update real-time location for live tracking."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    data = request.get_json(silent=True) or {}
    
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    
    if latitude is None or longitude is None:
        return jsonify({"success": False, "message": "Latitude and longitude required"}), 400
    
    try:
        assignment = delivery_assignments_col.find_one({
            "_id": ObjectId(assignment_id),
            "delivery_boy_id": delivery_boy_id
        })
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid assignment ID"}), 400
    
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404
    
    # Save location update
    location_doc = {
        "assignment_id": ObjectId(assignment_id),
        "delivery_boy_id": delivery_boy_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.now(timezone.utc)
    }
    delivery_locations_col.insert_one(location_doc)
    
    # Update latest location in delivery boy record
    delivery_boys_col.update_one(
        {"_id": delivery_boy_id},
        {
            "$set": {
                "current_latitude": latitude,
                "current_longitude": longitude,
                "last_location_update": datetime.now(timezone.utc)
            }
        }
    )
    
    return jsonify({
        "success": True,
        "message": "Location updated",
        "assignment_id": assignment_id
    }), 200


@delivery_bp.get("/history")
@delivery_boy_required
def get_delivery_history():
    """Get historical deliveries with filters and pagination."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")  # "delivered", "failed"
    
    skip = (page - 1) * limit
    
    query = {"delivery_boy_id": delivery_boy_id}
    if status:
        query["status"] = status
    
    history = list(delivery_assignments_col.find(query).sort("delivered_at", -1).skip(skip).limit(limit))
    total = delivery_assignments_col.count_documents(query)
    
    # Enrich with order data
    enriched = []
    for item in history:
        try:
            order = orders_col.find_one({"_id": ObjectId(item["order_id"])})
            enriched.append({
                "assignment_id": str(item["_id"]),
                "order_number": order.get("order_number") if order else None,
                "status": item.get("status"),
                "delivered_at": item.get("delivered_at").isoformat() if item.get("delivered_at") else None,
                "cod_collected": item.get("cod_collected", 0.0),
            })
        except:
            pass
    
    return jsonify({
        "success": True,
        "history": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        }
    }), 200


@delivery_bp.get("/earnings")
@delivery_boy_required
def get_earnings():
    """Get earnings summary. (Future ready - will be expanded)."""
    delivery_boy = request.current_delivery_boy
    
    return jsonify({
        "success": True,
        "earnings": {
            "total_earnings": delivery_boy.get("total_earnings", 0.0),
            "message": "Earnings details coming soon"
        }
    }), 200


@delivery_bp.post("/toggle-online")
@delivery_boy_required
def toggle_online():
    """Toggle delivery boy online/offline status."""
    delivery_boy_id = request.current_delivery_boy["_id"]
    data = request.get_json(silent=True) or {}
    is_online = data.get("is_online", False)
    
    now = datetime.now(timezone.utc)
    updates = {
        "is_online": is_online,
        "updated_at": now
    }
    
    if is_online:
        updates["online_since"] = now
    
    delivery_boys_col.update_one({"_id": delivery_boy_id}, {"$set": updates})
    
    return jsonify({
        "success": True,
        "message": f"Now {'online' if is_online else 'offline'}",
        "is_online": is_online
    }), 200


# ---------- Phase 3: Salary ----------

@delivery_bp.get("/salary")
@delivery_boy_required
def salary_history():
    """A delivery boy's own salary slip history (monthly salary + incentives
    + fuel allowance + bonus, minus attendance/other deductions/fines). This
    is separate from /api/delivery/earnings, which tracks per-delivery COD
    reconciliation, not the formal monthly Salary Module."""
    txns = list(salary_transactions_col.find(
        {"person_id": request.current_delivery_boy["_id"]}
    ).sort("month", -1))
    return jsonify({"success": True, "transactions": [serialize_salary_transaction(t) for t in txns]}), 200


@delivery_bp.get("/salary/<transaction_id>")
@delivery_boy_required
def salary_slip(transaction_id):
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid slip id"}), 400
    if not txn or txn["person_id"] != request.current_delivery_boy["_id"]:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404
    return jsonify({"success": True, "transaction": serialize_salary_transaction(txn)}), 200


@delivery_bp.get("/salary/<transaction_id>/pdf")
@delivery_boy_required
def salary_slip_pdf(transaction_id):
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid slip id"}), 400
    if not txn or txn["person_id"] != request.current_delivery_boy["_id"]:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404

    pdf_buffer = generate_salary_slip_pdf(txn)
    return send_file(
        pdf_buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"salary-slip-{txn['slip_number']}.pdf",
    )
