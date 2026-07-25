"""
SYRA Fresh - Validators
Lightweight validation helpers used across route handlers. Kept dependency-free
so they run identically on the server for every form the frontend submits.
"""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")          # Indian 10-digit mobile numbers
PINCODE_RE = re.compile(r"^\d{6}$")


def is_valid_email(email):
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def is_valid_phone(phone):
    return bool(phone) and bool(PHONE_RE.match(phone.strip()))


def is_valid_mobile(mobile):
    """Alias for is_valid_phone."""
    return is_valid_phone(mobile)


def is_valid_pincode(pincode):
    return bool(pincode) and bool(PINCODE_RE.match(str(pincode).strip()))


def is_strong_password(password):
    """At least 8 chars, one letter and one number."""
    if not password or len(password) < 8:
        return False
    return bool(re.search(r"[A-Za-z]", password)) and bool(re.search(r"\d", password))


def require_fields(data, fields):
    """Returns list of missing/empty field names."""
    missing = []
    for field in fields:
        value = data.get(field) if data else None
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def validate_registration(data):
    errors = {}
    missing = require_fields(data, ["name", "email", "password"])
    for f in missing:
        errors[f] = "This field is required"
    if "email" not in errors and not is_valid_email(data.get("email", "")):
        errors["email"] = "Enter a valid email address"
    if "password" not in errors and not is_strong_password(data.get("password", "")):
        errors["password"] = "Password must be at least 8 characters with a letter and a number"
    if data.get("phone") and not is_valid_phone(data.get("phone")):
        errors["phone"] = "Enter a valid 10-digit mobile number"
    return errors


def validate_address(data):
    errors = {}
    missing = require_fields(data, ["full_name", "phone", "line1", "city", "state", "pincode"])
    for f in missing:
        errors[f] = "This field is required"
    if "phone" not in errors and not is_valid_phone(data.get("phone", "")):
        errors["phone"] = "Enter a valid 10-digit mobile number"
    if "pincode" not in errors and not is_valid_pincode(data.get("pincode", "")):
        errors["pincode"] = "Enter a valid 6-digit pincode"
    return errors


def validate_product(data):
    errors = {}
    missing = require_fields(data, ["name", "category", "price"])
    for f in missing:
        errors[f] = "This field is required"
    try:
        if float(data.get("price", -1)) <= 0:
            errors["price"] = "Price must be greater than 0"
    except (TypeError, ValueError):
        errors["price"] = "Price must be a number"
    return errors


def validate_delivery_boy_registration(data):
    """Validate delivery boy registration form."""
    errors = {}
    required_fields = [
        "name", "email", "mobile", "password", "confirm_password",
        "address", "city", "state", "pincode", "aadhar_number",
        "vehicle_type", "vehicle_number", "delivery_area", "available_time"
    ]
    
    missing = require_fields(data, required_fields)
    for f in missing:
        errors[f] = "This field is required"
    
    # Email validation
    if "email" not in errors and not is_valid_email(data.get("email", "")):
        errors["email"] = "Enter a valid email address"
    
    # Mobile validation
    if "mobile" not in errors and not is_valid_mobile(data.get("mobile", "")):
        errors["mobile"] = "Enter a valid 10-digit mobile number"
    
    # Pincode validation
    if "pincode" not in errors and not is_valid_pincode(data.get("pincode", "")):
        errors["pincode"] = "Enter a valid 6-digit pincode"
    
    # Password validation
    if "password" not in errors:
        password = data.get("password", "")
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters"
    
    # Confirm password
    if data.get("password") != data.get("confirm_password"):
        errors["confirm_password"] = "Passwords do not match"
    
    # Alternate mobile validation
    alt_mobile = data.get("alternate_mobile")
    if alt_mobile and not is_valid_mobile(alt_mobile):
        errors["alternate_mobile"] = "Enter a valid 10-digit mobile number"
    
    # Aadhar validation (basic)
    aadhar = data.get("aadhar_number", "").replace(" ", "")
    if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
        errors["aadhar_number"] = "Enter a valid 12-digit Aadhar number"
    
    return errors
