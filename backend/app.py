"""
SYRA Fresh - Flask Application Entrypoint
Run with:  python app.py   (development)
Production: gunicorn -w 4 -b 0.0.0.0:8000 app:app
"""
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import config_by_name
from extensions import ensure_indexes

from routes.auth_routes import auth_bp
from routes.product_routes import products_bp
from routes.cart_routes import cart_bp
from routes.order_routes import orders_bp
from routes.review_routes import reviews_bp
from routes.admin_routes import admin_bp
from routes.delivery_auth_routes import delivery_auth_bp
from routes.delivery_routes import delivery_bp
from routes.admin_delivery_routes import admin_delivery_bp
from routes.notifications_routes import notifications_bp
from routes.admin_district_routes import admin_district_bp
from routes.admin_hub_routes import admin_hub_bp
from routes.admin_hub_manager_routes import admin_hub_manager_bp
from routes.hub_manager_auth_routes import hub_manager_auth_bp
from routes.hub_manager_routes import hub_manager_bp
from routes.public_hub_routes import public_hub_bp
from routes.admin_salary_routes import admin_salary_bp
from routes.contact_routes import contact_bp
from routes.admin_contact_routes import admin_contact_bp


def create_app():
    app = Flask(__name__)
    env = os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(delivery_auth_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(admin_delivery_bp)
    app.register_blueprint(notifications_bp)
    # Phase 2: District -> Hub -> Hub Manager
    app.register_blueprint(admin_district_bp)
    app.register_blueprint(admin_hub_bp)
    app.register_blueprint(admin_hub_manager_bp)
    app.register_blueprint(hub_manager_auth_bp)
    app.register_blueprint(hub_manager_bp)
    app.register_blueprint(public_hub_bp)
    # Phase 3: Salary Module
    app.register_blueprint(admin_salary_bp)
    # Contact Management System
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_contact_bp)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.route("/static/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/api/health")
    def health():
        return jsonify({"success": True, "service": "SYRA Fresh API", "status": "healthy"})

    # ---------- Error handlers ----------

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Something went wrong. Please try again."}), 500

    with app.app_context():
        try:
            ensure_indexes()
        except Exception as exc:
            app.logger.warning(f"Could not ensure indexes (is MongoDB running?): {exc}")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=app.config["DEBUG"])
