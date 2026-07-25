"""
SYRA Fresh - Hub Manager Panel Routes (Phase 2)

RBAC: every query below is filtered by request.current_hub_manager["hub_id"].
A Hub Manager can never see another hub's orders, delivery boys, customers,
or attendance - this is enforced route-by-route, not just at login.

GET  /api/hub-manager/dashboard
GET  /api/hub-manager/orders
POST /api/hub-manager/orders/<order_id>/assign
GET  /api/hub-manager/delivery-boys
PUT  /api/hub-manager/delivery-boys/<id>
GET  /api/hub-manager/customers
GET  /api/hub-manager/inventory                 (read-only, company-wide catalog)
GET  /api/hub-manager/attendance
POST /api/hub-manager/attendance/mark
GET  /api/hub-manager/reports
"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, send_file
from bson import ObjectId
from bson.errors import InvalidId

from extensions import (
    orders_col, delivery_boys_col, delivery_assignments_col, users_col,
    products_col, attendance_col, salary_transactions_col,
)
from models.order import serialize_order
from models.delivery_boy import serialize_delivery_boy_admin, new_delivery_assignment_doc
from models.product import serialize_product
from models.salary import serialize_salary_transaction
from utils.auth_utils import hub_manager_required
from utils.notification_service import NotificationService
from utils.pdf_generator import generate_salary_slip_pdf

hub_manager_bp = Blueprint("hub_manager", __name__, url_prefix="/api/hub-manager")


# ---------- Dashboard ----------

@hub_manager_bp.get("/dashboard")
@hub_manager_required
def dashboard():
    hub_id = request.current_hub_manager["hub_id"]

    total_delivery_boys = delivery_boys_col.count_documents({"hub_id": hub_id})
    active_delivery_boys = delivery_boys_col.count_documents({"hub_id": hub_id, "status": "approved"})

    total_orders = orders_col.count_documents({"hub_id": hub_id})
    pending_orders = orders_col.count_documents({"hub_id": hub_id, "status": {"$in": ["Placed", "Packed"]}})
    delivered_orders = orders_col.count_documents({"hub_id": hub_id, "status": "Delivered"})

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = orders_col.count_documents({"hub_id": hub_id, "created_at": {"$gte": today_start}})

    revenue_agg = list(orders_col.aggregate([
        {"$match": {"hub_id": hub_id, "status": {"$ne": "Cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$totals.total"}}},
    ]))
    total_revenue = revenue_agg[0]["total"] if revenue_agg else 0

    return jsonify({
        "success": True,
        "hub": {
            "name": request.current_hub_manager.get("hub_name"),
            "district": request.current_hub_manager.get("district_name"),
        },
        "stats": {
            "total_delivery_boys": total_delivery_boys,
            "active_delivery_boys": active_delivery_boys,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "delivered_orders": delivered_orders,
            "today_orders": today_orders,
            "total_revenue": total_revenue,
        },
    }), 200


# ---------- Orders ----------

@hub_manager_bp.get("/orders")
@hub_manager_required
def list_hub_orders():
    hub_id = request.current_hub_manager["hub_id"]
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")

    query = {"hub_id": hub_id}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    total = orders_col.count_documents(query)
    orders = list(orders_col.find(query).sort("created_at", -1).skip(skip).limit(limit))

    return jsonify({
        "success": True,
        "orders": [serialize_order(o) for o in orders],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit else 0},
    }), 200


@hub_manager_bp.post("/orders/<order_id>/assign")
@hub_manager_required
def assign_hub_order(order_id):
    """Assign an order to a delivery boy - both must belong to this manager's
    own hub. This is the Hub Manager equivalent of
    admin_delivery_routes.py::assign_order_to_delivery_boy, scoped down."""
    manager = request.current_hub_manager
    hub_id = manager["hub_id"]
    data = request.get_json(silent=True) or {}
    delivery_boy_id = data.get("delivery_boy_id")
    if not delivery_boy_id:
        return jsonify({"success": False, "message": "delivery_boy_id is required"}), 400

    try:
        order = orders_col.find_one({"_id": ObjectId(order_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid order ID"}), 400
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    if order.get("hub_id") != hub_id:
        return jsonify({"success": False, "message": "This order does not belong to your hub"}), 403

    try:
        delivery_boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    if not delivery_boy or delivery_boy.get("hub_id") != hub_id:
        return jsonify({"success": False, "message": "That delivery boy is not part of your hub"}), 403
    if delivery_boy.get("status") != "approved":
        return jsonify({"success": False, "message": "Delivery boy is not approved"}), 400

    if delivery_assignments_col.find_one({"order_id": order_id}):
        return jsonify({"success": False, "message": "Order already assigned"}), 400

    assignment_doc = new_delivery_assignment_doc(order_id, delivery_boy["_id"], delivery_boy.get("name"), manager["_id"])
    delivery_assignments_col.insert_one(assignment_doc)

    now = datetime.now(timezone.utc)
    orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {
            "delivery_boy_id": delivery_boy["_id"], "delivery_boy_name": delivery_boy.get("name"),
            "assigned_at": now, "assigned_by": manager["_id"], "status": "Packed", "updated_at": now,
        }, "$push": {"status_history": {"status": "Packed", "at": now}}},
    )

    try:
        NotificationService.notify_delivery_boy(delivery_boy["_id"], "order_assigned", "New Delivery Assignment",
                                                  f"You have been assigned order #{order.get('order_number')}")
    except Exception:
        pass

    updated = orders_col.find_one({"_id": order["_id"]})
    return jsonify({"success": True, "order": serialize_order(updated)}), 200


# ---------- Delivery Boys ----------

@hub_manager_bp.get("/delivery-boys")
@hub_manager_required
def list_hub_delivery_boys():
    hub_id = request.current_hub_manager["hub_id"]
    status = request.args.get("status")
    query = {"hub_id": hub_id}
    if status:
        query["status"] = status
    boys = list(delivery_boys_col.find(query).sort("created_at", -1))
    return jsonify({"success": True, "delivery_boys": [serialize_delivery_boy_admin(b) for b in boys]}), 200


@hub_manager_bp.put("/delivery-boys/<delivery_boy_id>")
@hub_manager_required
def update_hub_delivery_boy(delivery_boy_id):
    """Hub Managers may adjust operational fields for their own delivery
    boys, but cannot transfer them to another hub or change their approval
    status - those remain Super Admin-only (see admin_delivery_routes.py)."""
    hub_id = request.current_hub_manager["hub_id"]
    try:
        boy = delivery_boys_col.find_one({"_id": ObjectId(delivery_boy_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid delivery boy ID"}), 400
    if not boy or boy.get("hub_id") != hub_id:
        return jsonify({"success": False, "message": "That delivery boy is not part of your hub"}), 403

    data = request.get_json(silent=True) or {}
    updates = {k: data[k] for k in ["delivery_area", "available_time"] if k in data}
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400
    updates["updated_at"] = datetime.now(timezone.utc)

    delivery_boys_col.update_one({"_id": boy["_id"]}, {"$set": updates})
    updated = delivery_boys_col.find_one({"_id": boy["_id"]})
    return jsonify({"success": True, "delivery_boy": serialize_delivery_boy_admin(updated)}), 200


# ---------- Customers ----------

@hub_manager_bp.get("/customers")
@hub_manager_required
def list_hub_customers():
    """Customers who have placed at least one order routed to this hub."""
    hub_id = request.current_hub_manager["hub_id"]
    user_ids = orders_col.distinct("user_id", {"hub_id": hub_id})

    object_ids = []
    for uid in user_ids:
        try:
            object_ids.append(ObjectId(uid))
        except (InvalidId, TypeError):
            continue

    customers = list(users_col.find({"_id": {"$in": object_ids}})) if object_ids else []
    out = []
    for c in customers:
        order_count = orders_col.count_documents({"hub_id": hub_id, "user_id": str(c["_id"])})
        out.append({
            "id": str(c["_id"]), "name": c.get("name"), "email": c.get("email"),
            "mobile": c.get("mobile"), "order_count": order_count,
        })
    return jsonify({"success": True, "customers": out}), 200


# ---------- Inventory (read-only) ----------

@hub_manager_bp.get("/inventory")
@hub_manager_required
def hub_inventory():
    """SYRA Fresh currently runs a single shared product catalog/stock pool
    rather than per-hub warehousing, so this is a read-only view of the same
    company-wide inventory the Super Admin sees - Hub Managers can check
    stock levels here but stock changes remain Super Admin-only. Splitting
    inventory per-hub would be a larger schema change beyond this phase."""
    products = list(products_col.find().sort("name", 1))
    return jsonify({"success": True, "products": [serialize_product(p, detailed=True) for p in products]}), 200


# ---------- Attendance ----------

@hub_manager_bp.get("/attendance")
@hub_manager_required
def list_attendance():
    hub_id = request.current_hub_manager["hub_id"]
    date_str = request.args.get("date")  # YYYY-MM-DD, defaults to today
    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"success": False, "message": "date must be YYYY-MM-DD"}), 400
    else:
        day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    records = list(attendance_col.find({"hub_id": hub_id, "date": day}))
    boys = {str(b["_id"]): b.get("name") for b in delivery_boys_col.find({"hub_id": hub_id}, {"name": 1})}

    marked = {r["person_id"]: r for r in records}
    out = []
    for person_id, name in boys.items():
        rec = marked.get(person_id)
        out.append({
            "person_id": person_id, "name": name,
            "status": rec["status"] if rec else "not_marked",
            "marked_at": rec["marked_at"].isoformat() if rec and rec.get("marked_at") else None,
        })
    return jsonify({"success": True, "date": day.strftime("%Y-%m-%d"), "attendance": out}), 200


@hub_manager_bp.post("/attendance/mark")
@hub_manager_required
def mark_attendance():
    hub_id = request.current_hub_manager["hub_id"]
    data = request.get_json(silent=True) or {}
    person_id = data.get("person_id")
    status = data.get("status")  # present, absent, half_day, leave
    date_str = data.get("date")  # YYYY-MM-DD, defaults to today - must match
    # whatever date the Hub Manager has selected in the UI, otherwise a mark
    # made while viewing a past/future date would silently land on today.

    if status not in ("present", "absent", "half_day", "leave"):
        return jsonify({"success": False, "message": "status must be one of present/absent/half_day/leave"}), 400

    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"success": False, "message": "date must be YYYY-MM-DD"}), 400
    else:
        day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        boy = delivery_boys_col.find_one({"_id": ObjectId(person_id)})
    except (InvalidId, TypeError):
        boy = None
    if not boy or boy.get("hub_id") != hub_id:
        return jsonify({"success": False, "message": "That delivery boy is not part of your hub"}), 403

    now = datetime.now(timezone.utc)
    attendance_col.update_one(
        {"person_id": person_id, "date": day},
        {"$set": {
            "person_id": person_id, "person_name": boy.get("name"), "hub_id": hub_id,
            "date": day, "status": status, "marked_at": now, "marked_by": request.current_hub_manager["_id"],
        }},
        upsert=True,
    )
    return jsonify({"success": True, "message": "Attendance updated"}), 200


# ---------- Reports ----------

@hub_manager_bp.get("/reports")
@hub_manager_required
def hub_reports():
    hub_id = request.current_hub_manager["hub_id"]
    days = request.args.get("days", 30, type=int)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    daily = list(orders_col.aggregate([
        {"$match": {"hub_id": hub_id, "created_at": {"$gte": since}, "status": {"$ne": "Cancelled"}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "orders": {"$sum": 1}, "revenue": {"$sum": "$totals.total"},
        }},
        {"$sort": {"_id": 1}},
    ]))

    by_status = list(orders_col.aggregate([
        {"$match": {"hub_id": hub_id, "created_at": {"$gte": since}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]))

    top_delivery_boys = list(delivery_assignments_col.aggregate([
        {"$match": {"status": "delivered", "delivered_at": {"$gte": since}}},
        {"$lookup": {"from": "orders", "let": {"oid": "$order_id"},
                     "pipeline": [{"$match": {"$expr": {"$and": [
                         {"$eq": [{"$toString": "$_id"}, "$$oid"]}, {"$eq": ["$hub_id", hub_id]}]}}}],
                     "as": "order"}},
        {"$match": {"order": {"$ne": []}}},
        {"$group": {"_id": "$delivery_boy_name", "deliveries": {"$sum": 1}}},
        {"$sort": {"deliveries": -1}},
        {"$limit": 10},
    ]))

    return jsonify({
        "success": True,
        "daily": [{"date": d["_id"], "orders": d["orders"], "revenue": d["revenue"]} for d in daily],
        "by_status": [{"status": s["_id"], "count": s["count"]} for s in by_status],
        "top_delivery_boys": [{"name": t["_id"], "deliveries": t["deliveries"]} for t in top_delivery_boys],
    }), 200


# ---------- Salary (self-service, read-only) ----------
# Setting salary structures, generating slips, and paying remain
# Super Admin-only (see admin_salary_routes.py) - a Hub Manager can only
# ever view their own slip history here, never anyone else's or edit them.

@hub_manager_bp.get("/salary")
@hub_manager_required
def salary_history():
    txns = list(salary_transactions_col.find(
        {"person_id": request.current_hub_manager["_id"]}
    ).sort("month", -1))
    return jsonify({"success": True, "transactions": [serialize_salary_transaction(t) for t in txns]}), 200


@hub_manager_bp.get("/salary/<transaction_id>/pdf")
@hub_manager_required
def salary_slip_pdf(transaction_id):
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid slip id"}), 400
    if not txn or txn["person_id"] != request.current_hub_manager["_id"]:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404

    pdf_buffer = generate_salary_slip_pdf(txn)
    return send_file(
        pdf_buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"salary-slip-{txn['slip_number']}.pdf",
    )
