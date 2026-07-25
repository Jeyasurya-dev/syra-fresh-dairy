"""
SYRA Fresh - Public District/Hub Lookup Routes (Phase 2)
GET /api/districts               - active districts, for the delivery boy
                                    registration form's district dropdown
GET /api/hubs?district_id=<id>   - active hubs in a district, for the hub
                                    dropdown (required, since a delivery boy
                                    must pick both to determine which hub
                                    they belong to)

These are intentionally unauthenticated (unlike /api/admin/districts and
/api/admin/hubs) because delivery boy registration happens before login.
Only active districts/hubs are exposed here; admin endpoints see everything.
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from extensions import districts_col, hubs_col
from models.district import serialize_district
from models.hub import serialize_hub

public_hub_bp = Blueprint("public_hub", __name__, url_prefix="/api")


@public_hub_bp.get("/districts")
def list_active_districts():
    districts = list(districts_col.find({"is_active": True}).sort("name", 1))
    return jsonify({"success": True, "districts": [serialize_district(d) for d in districts]}), 200


@public_hub_bp.get("/hubs")
def list_active_hubs():
    district_id = request.args.get("district_id")
    if not district_id:
        return jsonify({"success": False, "message": "district_id is required"}), 400
    try:
        oid = ObjectId(district_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid district id"}), 400

    hubs = list(hubs_col.find({"district_id": oid, "is_active": True}).sort("name", 1))
    return jsonify({"success": True, "hubs": [serialize_hub(h) for h in hubs]}), 200
