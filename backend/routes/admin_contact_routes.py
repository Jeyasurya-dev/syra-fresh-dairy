"""
SYRA Fresh - Admin Contact Management Routes

Contact Messages:
  GET    /api/admin/contact-messages
  GET    /api/admin/contact-messages/<id>
  PUT    /api/admin/contact-messages/<id>/status     - Mark as Read / Closed / New
  DELETE /api/admin/contact-messages/<id>

Career Applications:
  GET    /api/admin/career-applications
  GET    /api/admin/career-applications/<id>
  PUT    /api/admin/career-applications/<id>/status  - Reviewing/Shortlisted/Rejected/Hired
  DELETE /api/admin/career-applications/<id>
  GET    /api/admin/career-applications/<id>/resume  - download the resume file
"""
import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from bson import ObjectId
from bson.errors import InvalidId

from extensions import contact_messages_col, career_applications_col
from models.contact import (
    serialize_contact_message, serialize_career_application,
    CONTACT_STATUSES, CAREER_STATUSES,
)
from utils.auth_utils import admin_required

admin_contact_bp = Blueprint("admin_contact", __name__, url_prefix="/api/admin")


def _paginated_query(collection, serializer, search_fields):
    """Shared list-with-search/filter/pagination logic for both Contact
    Messages and Career Applications - same shape, same query params
    (page, limit, status, search), so one implementation covers both."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status")
    search = request.args.get("search", "").strip()

    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [{field: {"$regex": search, "$options": "i"}} for field in search_fields]

    skip = (page - 1) * limit
    total = collection.count_documents(query)
    docs = list(collection.find(query).sort("created_at", -1).skip(skip).limit(limit))
    return {
        "items": [serializer(d) for d in docs],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit else 0},
    }


# ---------- Contact Messages ----------

@admin_contact_bp.get("/contact-messages")
@admin_required
def list_contact_messages():
    result = _paginated_query(contact_messages_col, serialize_contact_message, ["name", "email", "phone"])
    return jsonify({"success": True, "messages": result["items"], "pagination": result["pagination"]}), 200


@admin_contact_bp.get("/contact-messages/<message_id>")
@admin_required
def get_contact_message(message_id):
    try:
        doc = contact_messages_col.find_one({"_id": ObjectId(message_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid message id"}), 400
    if not doc:
        return jsonify({"success": False, "message": "Message not found"}), 404
    return jsonify({"success": True, "message_data": serialize_contact_message(doc)}), 200


@admin_contact_bp.put("/contact-messages/<message_id>/status")
@admin_required
def update_contact_message_status(message_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in CONTACT_STATUSES:
        return jsonify({"success": False, "message": f"Status must be one of {', '.join(CONTACT_STATUSES)}"}), 400
    try:
        oid = ObjectId(message_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid message id"}), 400

    result = contact_messages_col.update_one({"_id": oid}, {"$set": {"status": status}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Message not found"}), 404
    updated = contact_messages_col.find_one({"_id": oid})
    return jsonify({"success": True, "message_data": serialize_contact_message(updated)}), 200


@admin_contact_bp.delete("/contact-messages/<message_id>")
@admin_required
def delete_contact_message(message_id):
    try:
        oid = ObjectId(message_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid message id"}), 400
    result = contact_messages_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Message not found"}), 404
    return jsonify({"success": True}), 200


# ---------- Career Applications ----------

@admin_contact_bp.get("/career-applications")
@admin_required
def list_career_applications():
    result = _paginated_query(career_applications_col, serialize_career_application, ["name", "email", "phone", "position"])
    return jsonify({"success": True, "applications": result["items"], "pagination": result["pagination"]}), 200


@admin_contact_bp.get("/career-applications/<application_id>")
@admin_required
def get_career_application(application_id):
    try:
        doc = career_applications_col.find_one({"_id": ObjectId(application_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid application id"}), 400
    if not doc:
        return jsonify({"success": False, "message": "Application not found"}), 404
    return jsonify({"success": True, "application": serialize_career_application(doc)}), 200


@admin_contact_bp.put("/career-applications/<application_id>/status")
@admin_required
def update_career_application_status(application_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in CAREER_STATUSES:
        return jsonify({"success": False, "message": f"Status must be one of {', '.join(CAREER_STATUSES)}"}), 400
    try:
        oid = ObjectId(application_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid application id"}), 400

    result = career_applications_col.update_one({"_id": oid}, {"$set": {"status": status}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Application not found"}), 404
    updated = career_applications_col.find_one({"_id": oid})
    return jsonify({"success": True, "application": serialize_career_application(updated)}), 200


@admin_contact_bp.delete("/career-applications/<application_id>")
@admin_required
def delete_career_application(application_id):
    """Deletes the database record. The resume file on disk is intentionally
    left in place - if the application was ever exported/shared as part of a
    hiring workflow, silently deleting the underlying file out from under
    that could break something the admin doesn't realize depends on it.
    A cleanup script for orphaned resume files is a reasonable follow-up if
    disk usage ever becomes a concern."""
    try:
        oid = ObjectId(application_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid application id"}), 400
    result = career_applications_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Application not found"}), 404
    return jsonify({"success": True}), 200


@admin_contact_bp.get("/career-applications/<application_id>/resume")
@admin_required
def download_resume(application_id):
    """Download Resume - streams the file as an attachment. (View Resume,
    from the admin UI, just opens the same /static/uploads/resumes/... URL
    directly in a new tab, which the browser renders inline for PDFs.)"""
    try:
        doc = career_applications_col.find_one({"_id": ObjectId(application_id)})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid application id"}), 400
    if not doc or not doc.get("resume_path"):
        return jsonify({"success": False, "message": "Resume not found"}), 404

    # resume_path is stored as "/static/uploads/resumes/<filename>" - pull
    # just the filename back out and re-join it under the real uploads
    # folder rather than trusting any part of the stored path directly.
    filename = os.path.basename(doc["resume_path"])
    resumes_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes")
    return send_from_directory(
        resumes_dir, filename, as_attachment=True,
        download_name=doc.get("resume_file") or filename,
    )
