"""
SYRA Fresh - Delivery Boy Model
"""
from datetime import datetime, timezone


def new_delivery_boy_doc(name, email, mobile, password_hash, address_data, document_data, hub_id=None, hub_name=None):
    """
    Create a new delivery boy registration document.
    
    document_data: {aadhar_number, aadhar_front_url, aadhar_back_url, license_number, 
                   license_url, vehicle_type, vehicle_number, profile_photo_url, 
                   emergency_contact, delivery_area, available_time, upi_id, bank_details}
    hub_id/hub_name: Phase 2 - the hub this delivery boy is assigned to,
        resolved from the district+hub selected at registration. Can be
        changed later by the Super Admin (transfer).
    """
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "mobile": mobile.strip(),
        "alternate_mobile": document_data.get("alternate_mobile"),
        "password_hash": password_hash,
        "role": "delivery_boy",
        
        # Personal Info
        "address": address_data.get("address"),
        "city": address_data.get("city"),
        "district": address_data.get("district"),
        "state": address_data.get("state"),
        "pincode": address_data.get("pincode"),
        
        # Documents
        "aadhar_number": document_data.get("aadhar_number"),
        "aadhar_front_url": document_data.get("aadhar_front_url"),
        "aadhar_back_url": document_data.get("aadhar_back_url"),
        "license_number": document_data.get("license_number"),
        "license_url": document_data.get("license_url"),
        
        # Vehicle Info
        "vehicle_type": document_data.get("vehicle_type"),  # "bike", "scooter", "car"
        "vehicle_number": document_data.get("vehicle_number"),
        
        # Operational Details
        "profile_photo_url": document_data.get("profile_photo_url"),
        "emergency_contact": document_data.get("emergency_contact"),
        "delivery_area": document_data.get("delivery_area"),
        "available_time": document_data.get("available_time"),  # "morning", "afternoon", "evening", "full_day"

        # Phase 2: Hub assignment
        "hub_id": hub_id,
        "hub_name": hub_name,
        
        # Financial Info (future ready)
        "upi_id": document_data.get("upi_id"),
        "bank_details": document_data.get("bank_details"),  # {account_number, ifsc, bank_name, account_holder}
        
        # Status Management
        "status": "pending_verification",  # pending_verification, approved, rejected, suspended, deactivated
        "verification_notes": None,
        "verified_by": None,
        "verified_at": None,
        
        # Performance Metrics
        "total_deliveries": 0,
        "successful_deliveries": 0,
        "failed_deliveries": 0,
        "rating": 5.0,
        "total_earnings": 0.0,
        
        # Tracking
        "current_latitude": None,
        "current_longitude": None,
        "last_location_update": None,
        "is_online": False,
        "online_since": None,
        
        # Timestamps
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def new_delivery_assignment_doc(order_id, delivery_boy_id, delivery_boy_name, assigned_by_admin_id):
    """Create delivery assignment record."""
    return {
        "order_id": order_id,
        "delivery_boy_id": delivery_boy_id,
        "delivery_boy_name": delivery_boy_name,
        "assigned_by": assigned_by_admin_id,
        "status": "assigned",  # assigned, picked_up, out_for_delivery, delivered, failed
        "assigned_at": datetime.now(timezone.utc),
        "picked_up_at": None,
        "out_for_delivery_at": None,
        "delivered_at": None,
        "failure_reason": None,
        "delivery_notes": None,
        "cod_collected": 0.0,
        "cod_submitted": False,
        "cod_submitted_at": None,
        "distance_traveled": 0.0,
        "estimated_delivery_time": None,
        "actual_delivery_time": None,
        "updated_at": datetime.now(timezone.utc),
    }


def serialize_delivery_boy(doc):
    """Serialize delivery boy for API response."""
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "mobile": doc.get("mobile"),
        "alternate_mobile": doc.get("alternate_mobile"),
        "address": doc.get("address"),
        "city": doc.get("city"),
        "district": doc.get("district"),
        "state": doc.get("state"),
        "pincode": doc.get("pincode"),
        "vehicle_type": doc.get("vehicle_type"),
        "vehicle_number": doc.get("vehicle_number"),
        "profile_photo_url": doc.get("profile_photo_url"),
        "delivery_area": doc.get("delivery_area"),
        "available_time": doc.get("available_time"),
        "hub_id": str(doc["hub_id"]) if doc.get("hub_id") else None,
        "hub_name": doc.get("hub_name"),
        "status": doc.get("status"),
        "total_deliveries": doc.get("total_deliveries", 0),
        "successful_deliveries": doc.get("successful_deliveries", 0),
        "failed_deliveries": doc.get("failed_deliveries", 0),
        "rating": doc.get("rating", 5.0),
        "total_earnings": doc.get("total_earnings", 0.0),
        "is_online": doc.get("is_online", False),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }


def serialize_delivery_boy_admin(doc):
    """Full serialization for admin view."""
    if not doc:
        return None
    data = serialize_delivery_boy(doc)
    data.update({
        "aadhar_number": doc.get("aadhar_number"),
        "aadhar_front_url": doc.get("aadhar_front_url"),
        "aadhar_back_url": doc.get("aadhar_back_url"),
        "license_number": doc.get("license_number"),
        "license_url": doc.get("license_url"),
        "emergency_contact": doc.get("emergency_contact"),
        "upi_id": doc.get("upi_id"),
        "bank_details": doc.get("bank_details"),
        "verification_notes": doc.get("verification_notes"),
        "verified_by": str(doc.get("verified_by")) if doc.get("verified_by") else None,
        "verified_at": doc.get("verified_at").isoformat() if doc.get("verified_at") else None,
    })
    return data
