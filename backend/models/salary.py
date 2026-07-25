"""
SYRA Fresh - Salary Module (Phase 3)

Two collections:
  salary_structures_col   - one active pay structure per person (Hub Manager
                             or Delivery Boy): monthly base, per-order
                             incentive rate, fuel allowance.
  salary_transactions_col - one record per person per month, generated from
                             that structure plus that month's actual
                             deliveries/attendance, with room for the Super
                             Admin to add a bonus/fine/other deduction
                             before marking it Paid. This is the "salary
                             slip" + "salary transaction history" that
                             persists even if the underlying structure
                             changes later.
"""
import random
import string
from datetime import datetime, timezone


def generate_slip_number():
    date_part = datetime.now(timezone.utc).strftime("%y%m")
    rand_part = "".join(random.choices(string.digits, k=6))
    return f"SLIP{date_part}{rand_part}"


# ---------- Salary Structure ----------

def new_salary_structure_doc(person_type, person_id, person_name, hub_id, hub_name,
                              monthly_salary, per_order_incentive=0, fuel_allowance=0,
                              per_day_wage=None):
    """
    person_type: "hub_manager" | "delivery_boy"
    per_day_wage: used for attendance-based deductions; defaults to
        monthly_salary / 30 if not given explicitly.
    """
    now = datetime.now(timezone.utc)
    return {
        "person_type": person_type,
        "person_id": person_id,
        "person_name": person_name,
        "hub_id": hub_id,
        "hub_name": hub_name,
        "monthly_salary": float(monthly_salary),
        "per_order_incentive": float(per_order_incentive),
        "fuel_allowance": float(fuel_allowance),
        "per_day_wage": float(per_day_wage) if per_day_wage is not None else round(float(monthly_salary) / 30, 2),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


def serialize_salary_structure(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "person_type": doc.get("person_type"),
        "person_id": str(doc.get("person_id")),
        "person_name": doc.get("person_name"),
        "hub_id": str(doc.get("hub_id")) if doc.get("hub_id") else None,
        "hub_name": doc.get("hub_name"),
        "monthly_salary": doc.get("monthly_salary"),
        "per_order_incentive": doc.get("per_order_incentive"),
        "fuel_allowance": doc.get("fuel_allowance"),
        "per_day_wage": doc.get("per_day_wage"),
        "is_active": doc.get("is_active", True),
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


# ---------- Salary Transaction (slip) ----------

def new_salary_transaction_doc(person_type, person_id, person_name, hub_id, hub_name, month,
                                monthly_salary, orders_delivered, per_order_incentive_rate,
                                fuel_allowance, attendance_present, attendance_half_day,
                                attendance_absent, attendance_deduction, generated_by):
    now = datetime.now(timezone.utc)
    per_order_incentive_total = round(orders_delivered * per_order_incentive_rate, 2)
    gross_earnings = round(monthly_salary + per_order_incentive_total + fuel_allowance, 2)
    total_deductions = round(attendance_deduction, 2)
    net_pay = round(gross_earnings - total_deductions, 2)

    return {
        "slip_number": generate_slip_number(),
        "person_type": person_type,
        "person_id": person_id,
        "person_name": person_name,
        "hub_id": hub_id,
        "hub_name": hub_name,
        "month": month,  # "YYYY-MM"

        "breakdown": {
            "monthly_salary": monthly_salary,
            "orders_delivered": orders_delivered,
            "per_order_incentive_rate": per_order_incentive_rate,
            "per_order_incentive_total": per_order_incentive_total,
            "fuel_allowance": fuel_allowance,
            "bonus": 0.0,
            "attendance_present_days": attendance_present,
            "attendance_half_days": attendance_half_day,
            "attendance_absent_days": attendance_absent,
            "attendance_deduction": attendance_deduction,
            "other_deductions": 0.0,
            "fine": 0.0,
            "fine_reason": None,
        },

        "gross_earnings": gross_earnings,
        "total_deductions": total_deductions,
        "net_pay": net_pay,

        "status": "pending",  # pending | paid
        "generated_at": now,
        "generated_by": generated_by,
        "paid_at": None,
        "paid_by": None,
        "payment_reference": None,
        "updated_at": now,
    }


def recompute_transaction_totals(doc):
    """Recompute gross/net after an admin adjusts bonus/other_deductions/fine
    on a still-pending transaction. Mutates and returns the breakdown dict's
    parent fields; caller is responsible for persisting via update_one."""
    b = doc["breakdown"]
    gross = round(b["monthly_salary"] + b["per_order_incentive_total"] + b["fuel_allowance"] + b.get("bonus", 0), 2)
    deductions = round(b.get("attendance_deduction", 0) + b.get("other_deductions", 0) + b.get("fine", 0), 2)
    doc["gross_earnings"] = gross
    doc["total_deductions"] = deductions
    doc["net_pay"] = round(gross - deductions, 2)
    return doc


def serialize_salary_transaction(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "slip_number": doc.get("slip_number"),
        "person_type": doc.get("person_type"),
        "person_id": str(doc.get("person_id")),
        "person_name": doc.get("person_name"),
        "hub_id": str(doc.get("hub_id")) if doc.get("hub_id") else None,
        "hub_name": doc.get("hub_name"),
        "month": doc.get("month"),
        "breakdown": doc.get("breakdown"),
        "gross_earnings": doc.get("gross_earnings"),
        "total_deductions": doc.get("total_deductions"),
        "net_pay": doc.get("net_pay"),
        "status": doc.get("status"),
        "generated_at": doc.get("generated_at").isoformat() if doc.get("generated_at") else None,
        "paid_at": doc.get("paid_at").isoformat() if doc.get("paid_at") else None,
        "payment_reference": doc.get("payment_reference"),
    }
