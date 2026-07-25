"""
SYRA Fresh - Contact Management System (public submission endpoint)

POST /api/contact

Accepts multipart/form-data always (so an optional resume file can ride
along uniformly). Routes to one of two collections based on `topic`:
  - topic == "Careers / Job Application" -> career_applications_col
    (requires position, location, and a resume file)
  - anything else -> contact_messages_col (general contact form)

No emails are sent for either path - both just land in MongoDB for the
Super Admin to review in the Contact Messages / Career Applications pages.
"""
import os
import random
import string
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from extensions import contact_messages_col, career_applications_col
from models.contact import (
    new_contact_message_doc, serialize_contact_message,
    new_career_application_doc, serialize_career_application,
    CAREER_TOPIC,
)
from utils.validators import is_valid_email, is_valid_mobile

contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")


def _allowed_resume_extension(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_RESUME_EXTENSIONS"]


def _validate_resume(file_storage):
    """Check presence/extension/size without touching disk. Returns an
    error message, or None if the file is fine to save."""
    if not file_storage or file_storage.filename == "":
        return "Resume file is required"
    if not _allowed_resume_extension(file_storage.filename):
        return "Only PDF, DOC, or DOCX files are allowed"

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        return "Resume file is empty"
    if size > current_app.config["MAX_RESUME_SIZE"]:
        return "Resume file must be 5 MB or smaller"
    return None


def _save_resume_file(file_storage):
    """Securely save an already-validated resume into
    static/uploads/resumes/ and return its public URL (e.g.
    "/static/uploads/resumes/xxx.pdf") - same convention as
    save_upload_file() in delivery_auth_routes.py, fixed there in an
    earlier pass to always include the "/static/uploads" prefix.

    Security:
    - werkzeug's secure_filename() strips path separators and any other
      characters that could enable directory traversal (e.g. "../../etc").
    - A timestamp + random suffix is appended and we confirm the resulting
      path doesn't already exist (looping if it somehow does) - so this can
      never silently overwrite another applicant's resume, and unique
      filenames are guaranteed rather than merely assumed.
    """
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    base = original.rsplit(".", 1)[0] or "resume"

    resumes_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes")
    os.makedirs(resumes_dir, exist_ok=True)

    for _ in range(5):  # practically always succeeds on the first try
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        rand_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        filename = f"{timestamp}_{rand_part}_{base}.{ext}"
        filepath = os.path.join(resumes_dir, filename)
        if not os.path.exists(filepath):
            file_storage.save(filepath)
            return f"/static/uploads/resumes/{filename}"

    return None


@contact_bp.post("")
def submit_contact():
    data = request.form.to_dict()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    topic = (data.get("topic") or "").strip()
    message = (data.get("message") or "").strip()

    errors = {}
    if not name:
        errors["name"] = "Full name is required"
    if not is_valid_email(email):
        errors["email"] = "Enter a valid email address"
    if not is_valid_mobile(phone):
        errors["phone"] = "Enter a valid 10-digit mobile number"
    if not topic:
        errors["topic"] = "Please select a topic"

    is_career = topic == CAREER_TOPIC
    resume = None

    if is_career:
        location = (data.get("location") or "").strip()
        position = (data.get("position") or "").strip()
        if not position:
            errors["position"] = "Position applying for is required"
        if not location:
            errors["location"] = "Current location is required"

        resume = request.files.get("resume")
        resume_error = _validate_resume(resume)
        if resume_error:
            errors["resume"] = resume_error
    else:
        if not message:
            errors["message"] = "Message is required"

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if is_career:
        resume_path = _save_resume_file(resume)
        if not resume_path:
            return jsonify({"success": False, "message": "Could not save your resume. Please try again."}), 500
        doc = new_career_application_doc(name, email, phone, location, position, resume.filename, resume_path)
        result = career_applications_col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return jsonify({
            "success": True,
            "message": "Your application has been received. Our team will review it and reach out if there's a match.",
            "application": serialize_career_application(doc),
        }), 201

    doc = new_contact_message_doc(name, email, phone, topic, message)
    result = contact_messages_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({
        "success": True,
        "message": "Thanks! We've received your message and will get back to you shortly.",
        "contact_message": serialize_contact_message(doc),
    }), 201
