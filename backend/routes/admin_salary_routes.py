"""
SYRA Fresh - Admin Salary Management Routes (Phase 3)

GET    /api/admin/salary/structures                         - list all pay structures
GET    /api/admin/salary/structures/<person_type>/<person_id>
POST   /api/admin/salary/structures                         - create/update (upsert) a pay structure
POST   /api/admin/salary/generate                            - generate one person's slip for a month
POST   /api/admin/salary/generate-bulk                        - generate for every person of a type (optionally one hub)
GET    /api/admin/salary/transactions                         - list slips, filterable
GET    /api/admin/salary/transactions/<id>
PUT    /api/admin/salary/transactions/<id>/adjust             - bonus / other_deductions / fine (pending only)
POST   /api/admin/salary/transactions/<id>/pay                - Pay Salary button
DELETE /api/admin/salary/transactions/<id>                    - undo a pending (unpaid) slip
"""
import calendar
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file
from bson import ObjectId
from bson.errors import InvalidId

from extensions import (
    salary_structures_col, salary_transactions_col, hub_managers_col,
    delivery_boys_col, delivery_assignments_col, attendance_col,
)
from models.salary import (
    new_salary_structure_doc, serialize_salary_structure,
    new_salary_transaction_doc, serialize_salary_transaction, recompute_transaction_totals,
)
from utils.auth_utils import admin_required
from utils.pdf_generator import generate_salary_slip_pdf

admin_salary_bp = Blueprint("admin_salary", __name__, url_prefix="/api/admin/salary")


def _find_person(person_type, person_id):
    """Look up a Hub Manager or Delivery Boy by id, returning (doc, hub_id, hub_name) or (None, None, None)."""
    try:
        oid = ObjectId(person_id)
    except InvalidId:
        return None, None, None
    if person_type == "hub_manager":
        doc = hub_managers_col.find_one({"_id": oid})
    elif person_type == "delivery_boy":
        doc = delivery_boys_col.find_one({"_id": oid})
    else:
        return None, None, None
    if not doc:
        return None, None, None
    return doc, doc.get("hub_id"), doc.get("hub_name")


def _month_bounds(month_str):
    """month_str = 'YYYY-MM' -> (start_datetime_utc, end_datetime_utc_exclusive)"""
    year, month = (int(x) for x in month_str.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end, last_day


# ---------- Salary Structures ----------

@admin_salary_bp.get("/structures")
@admin_required
def list_structures():
    person_type = request.args.get("person_type")
    query = {}
    if person_type:
        query["person_type"] = person_type
    structures = list(salary_structures_col.find(query).sort("person_name", 1))
    return jsonify({"success": True, "structures": [serialize_salary_structure(s) for s in structures]}), 200


@admin_salary_bp.get("/structures/<person_type>/<person_id>")
@admin_required
def get_structure(person_type, person_id):
    try:
        oid = ObjectId(person_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid person id"}), 400
    structure = salary_structures_col.find_one({"person_type": person_type, "person_id": oid})
    return jsonify({"success": True, "structure": serialize_salary_structure(structure)}), 200


@admin_salary_bp.post("/structures")
@admin_required
def upsert_structure():
    """Set Salary: create the structure if none exists yet for this person,
    otherwise update it. Existing generated slips for past months are never
    retroactively changed - only future `generate` calls use the new rates."""
    data = request.get_json(silent=True) or {}
    person_type = data.get("person_type")
    person_id = data.get("person_id")
    if person_type not in ("hub_manager", "delivery_boy"):
        return jsonify({"success": False, "message": "person_type must be hub_manager or delivery_boy"}), 400

    person, hub_id, hub_name = _find_person(person_type, person_id)
    if not person:
        return jsonify({"success": False, "message": "Person not found"}), 404

    try:
        monthly_salary = float(data.get("monthly_salary", 0))
        per_order_incentive = float(data.get("per_order_incentive", 0))
        fuel_allowance = float(data.get("fuel_allowance", 0))
        per_day_wage = data.get("per_day_wage")
        per_day_wage = float(per_day_wage) if per_day_wage not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Salary fields must be numbers"}), 400

    if monthly_salary < 0 or per_order_incentive < 0 or fuel_allowance < 0:
        return jsonify({"success": False, "message": "Salary fields cannot be negative"}), 400

    existing = salary_structures_col.find_one({"person_type": person_type, "person_id": person["_id"]})
    if existing:
        updates = {
            "monthly_salary": monthly_salary, "per_order_incentive": per_order_incentive,
            "fuel_allowance": fuel_allowance,
            "per_day_wage": per_day_wage if per_day_wage is not None else round(monthly_salary / 30, 2),
            "hub_id": hub_id, "hub_name": hub_name, "person_name": person.get("name"),
            "updated_at": datetime.now(timezone.utc),
        }
        salary_structures_col.update_one({"_id": existing["_id"]}, {"$set": updates})
        updated = salary_structures_col.find_one({"_id": existing["_id"]})
        return jsonify({"success": True, "structure": serialize_salary_structure(updated)}), 200

    doc = new_salary_structure_doc(
        person_type, person["_id"], person.get("name"), hub_id, hub_name,
        monthly_salary, per_order_incentive, fuel_allowance, per_day_wage,
    )
    result = salary_structures_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "structure": serialize_salary_structure(doc)}), 201


# ---------- Generate salary slips ----------

def _generate_one(person_type, person, structure, month, generated_by):
    """Core generation logic shared by single + bulk generate. Returns
    (transaction_doc, error_message). Skips (returns None, reason) if a slip
    already exists for this person+month - generation is not a way to
    silently overwrite an already-generated or already-paid slip; use
    `adjust` for pending ones or delete-then-regenerate deliberately."""
    if salary_transactions_col.find_one({"person_id": person["_id"], "month": month}):
        return None, f"A salary slip for {person.get('name')} already exists for {month}"

    start, end, days_in_month = _month_bounds(month)

    orders_delivered = 0
    if person_type == "delivery_boy":
        orders_delivered = delivery_assignments_col.count_documents({
            "delivery_boy_id": person["_id"], "status": "delivered",
            "delivered_at": {"$gte": start, "$lte": end},
        })

    # Attendance-based salary: count days marked in this month for this
    # person and deduct proportionally for absences / half the day-wage for
    # half-days. Days never marked at all are not penalized (e.g. before the
    # person joined) - only explicit "absent"/"half_day" markings deduct.
    att_records = list(attendance_col.find({
        "person_id": str(person["_id"]), "date": {"$gte": start, "$lte": end},
    }))
    present = sum(1 for a in att_records if a["status"] == "present")
    half_day = sum(1 for a in att_records if a["status"] == "half_day")
    absent = sum(1 for a in att_records if a["status"] == "absent")

    per_day_wage = structure.get("per_day_wage") or round(structure["monthly_salary"] / 30, 2)
    attendance_deduction = round(absent * per_day_wage + half_day * (per_day_wage / 2), 2)

    doc = new_salary_transaction_doc(
        person_type, person["_id"], person.get("name"), structure.get("hub_id"), structure.get("hub_name"),
        month, structure["monthly_salary"], orders_delivered, structure["per_order_incentive"],
        structure["fuel_allowance"], present, half_day, absent, attendance_deduction, generated_by,
    )
    result = salary_transactions_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc, None


@admin_salary_bp.post("/generate")
@admin_required
def generate_salary():
    data = request.get_json(silent=True) or {}
    person_type = data.get("person_type")
    person_id = data.get("person_id")
    month = data.get("month")  # "YYYY-MM"

    if person_type not in ("hub_manager", "delivery_boy"):
        return jsonify({"success": False, "message": "person_type must be hub_manager or delivery_boy"}), 400
    if not month:
        return jsonify({"success": False, "message": "month (YYYY-MM) is required"}), 400

    person, hub_id, hub_name = _find_person(person_type, person_id)
    if not person:
        return jsonify({"success": False, "message": "Person not found"}), 404

    structure = salary_structures_col.find_one({"person_type": person_type, "person_id": person["_id"]})
    if not structure:
        return jsonify({"success": False, "message": "No salary structure set for this person yet. Set their salary first."}), 400

    doc, err = _generate_one(person_type, person, structure, month, request.current_admin["_id"])
    if err:
        return jsonify({"success": False, "message": err}), 409
    return jsonify({"success": True, "transaction": serialize_salary_transaction(doc)}), 201


@admin_salary_bp.post("/generate-bulk")
@admin_required
def generate_salary_bulk():
    data = request.get_json(silent=True) or {}
    person_type = data.get("person_type")
    month = data.get("month")
    hub_id_filter = data.get("hub_id")

    if person_type not in ("hub_manager", "delivery_boy"):
        return jsonify({"success": False, "message": "person_type must be hub_manager or delivery_boy"}), 400
    if not month:
        return jsonify({"success": False, "message": "month (YYYY-MM) is required"}), 400

    collection = hub_managers_col if person_type == "hub_manager" else delivery_boys_col
    query = {}
    if person_type == "delivery_boy":
        query["status"] = "approved"
    if hub_id_filter:
        try:
            query["hub_id"] = ObjectId(hub_id_filter)
        except InvalidId:
            return jsonify({"success": False, "message": "Invalid hub id"}), 400

    people = list(collection.find(query))
    generated, skipped = [], []
    for person in people:
        structure = salary_structures_col.find_one({"person_type": person_type, "person_id": person["_id"]})
        if not structure:
            skipped.append({"person_name": person.get("name"), "reason": "No salary structure set"})
            continue
        doc, err = _generate_one(person_type, person, structure, month, request.current_admin["_id"])
        if err:
            skipped.append({"person_name": person.get("name"), "reason": err})
        else:
            generated.append(serialize_salary_transaction(doc))

    return jsonify({"success": True, "generated": generated, "skipped": skipped,
                     "generated_count": len(generated), "skipped_count": len(skipped)}), 200


# ---------- Salary Transactions (slips) ----------

@admin_salary_bp.get("/transactions")
@admin_required
def list_transactions():
    query = {}
    for field in ("person_type", "status", "month"):
        value = request.args.get(field)
        if value:
            query[field] = value
    hub_id = request.args.get("hub_id")
    if hub_id:
        try:
            query["hub_id"] = ObjectId(hub_id)
        except InvalidId:
            return jsonify({"success": False, "message": "Invalid hub id"}), 400

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    total = salary_transactions_col.count_documents(query)
    txns = list(salary_transactions_col.find(query).sort("generated_at", -1).skip(skip).limit(limit))
    return jsonify({
        "success": True,
        "transactions": [serialize_salary_transaction(t) for t in txns],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit else 0},
    }), 200


@admin_salary_bp.get("/transactions/<transaction_id>")
@admin_required
def get_transaction(transaction_id):
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid transaction id"}), 400
    if not txn:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404
    return jsonify({"success": True, "transaction": serialize_salary_transaction(txn)}), 200


@admin_salary_bp.get("/transactions/<transaction_id>/pdf")
@admin_required
def download_transaction_pdf(transaction_id):
    """Generate Salary Slip PDF - a real PDF file, not just the printable
    HTML slip page (frontend/admin/salary-slip.html can still be used for a
    quick on-screen look; this is for an actual downloadable/emailable file)."""
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid transaction id"}), 400
    if not txn:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404

    pdf_buffer = generate_salary_slip_pdf(txn)
    return send_file(
        pdf_buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"salary-slip-{txn['slip_number']}.pdf",
    )


@admin_salary_bp.put("/transactions/<transaction_id>/adjust")
@admin_required
def adjust_transaction(transaction_id):
    """Add/update Bonus, other deductions, and Fine on a still-pending slip.
    Once a slip is Paid it's a locked financial record - adjustments are
    blocked to keep the paid-history trustworthy."""
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid transaction id"}), 400
    if not txn:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404
    if txn["status"] == "paid":
        return jsonify({"success": False, "message": "Cannot adjust a slip that has already been paid"}), 409

    data = request.get_json(silent=True) or {}
    try:
        if "bonus" in data:
            txn["breakdown"]["bonus"] = max(0.0, float(data["bonus"]))
        if "other_deductions" in data:
            txn["breakdown"]["other_deductions"] = max(0.0, float(data["other_deductions"]))
        if "fine" in data:
            txn["breakdown"]["fine"] = max(0.0, float(data["fine"]))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Bonus/deduction/fine must be numbers"}), 400
    if "fine_reason" in data:
        txn["breakdown"]["fine_reason"] = (data.get("fine_reason") or "").strip() or None

    txn = recompute_transaction_totals(txn)
    txn["updated_at"] = datetime.now(timezone.utc)
    salary_transactions_col.update_one({"_id": txn["_id"]}, {"$set": {
        "breakdown": txn["breakdown"], "gross_earnings": txn["gross_earnings"],
        "total_deductions": txn["total_deductions"], "net_pay": txn["net_pay"], "updated_at": txn["updated_at"],
    }})
    return jsonify({"success": True, "transaction": serialize_salary_transaction(txn)}), 200


@admin_salary_bp.post("/transactions/<transaction_id>/pay")
@admin_required
def pay_transaction(transaction_id):
    """The 'Pay Salary' button - marks a slip as Paid."""
    try:
        txn = salary_transactions_col.find_one({"_id": ObjectId(transaction_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid transaction id"}), 400
    if not txn:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404
    if txn["status"] == "paid":
        return jsonify({"success": False, "message": "This slip has already been paid"}), 409

    data = request.get_json(silent=True) or {}
    now = datetime.now(timezone.utc)
    salary_transactions_col.update_one({"_id": txn["_id"]}, {"$set": {
        "status": "paid", "paid_at": now, "paid_by": request.current_admin["_id"],
        "payment_reference": (data.get("payment_reference") or "").strip() or None,
        "updated_at": now,
    }})
    updated = salary_transactions_col.find_one({"_id": txn["_id"]})
    return jsonify({"success": True, "transaction": serialize_salary_transaction(updated)}), 200


@admin_salary_bp.delete("/transactions/<transaction_id>")
@admin_required
def delete_transaction(transaction_id):
    try:
        oid = ObjectId(transaction_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid transaction id"}), 400
    txn = salary_transactions_col.find_one({"_id": oid})
    if not txn:
        return jsonify({"success": False, "message": "Salary slip not found"}), 404
    if txn["status"] == "paid":
        return jsonify({"success": False, "message": "Cannot delete a slip that has already been paid"}), 409
    salary_transactions_col.delete_one({"_id": oid})
    return jsonify({"success": True}), 200
