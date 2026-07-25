"""
SYRA Fresh - Contact Management System

Two distinct document shapes, sharing a single public submission endpoint
(POST /api/contact) that routes to one or the other based on the selected
topic:

  contact_messages     - general contact form submissions (support,
                          feedback, partnerships, etc.)
  career_applications  - submissions where topic == "Careers / Job
                          Application", which carry extra fields and a
                          resume file instead of being routed to email.
"""
from datetime import datetime, timezone

CONTACT_STATUSES = ["New", "Read", "Closed"]
CAREER_STATUSES = ["New", "Reviewing", "Shortlisted", "Rejected", "Hired"]
CAREER_TOPIC = "Careers / Job Application"


# ---------- Contact Messages ----------

def new_contact_message_doc(name, email, phone, topic, message):
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "phone": phone.strip(),
        "topic": topic.strip(),
        "message": message.strip(),
        "status": "New",
        "created_at": now,
        "updated_at": now,
    }


def serialize_contact_message(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "topic": doc.get("topic"),
        "message": doc.get("message"),
        "status": doc.get("status"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }


# ---------- Career Applications ----------

def new_career_application_doc(name, email, phone, location, position, resume_file, resume_path):
    now = datetime.now(timezone.utc)
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "phone": phone.strip(),
        "location": location.strip(),
        "position": position.strip(),
        "resume_file": resume_file,   # original filename, for display
        "resume_path": resume_path,   # served URL, e.g. /static/uploads/resumes/xxx.pdf
        "status": "New",
        "created_at": now,
        "updated_at": now,
    }


def serialize_career_application(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "location": doc.get("location"),
        "position": doc.get("position"),
        "resume_file": doc.get("resume_file"),
        "resume_path": doc.get("resume_path"),
        "status": doc.get("status"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }
