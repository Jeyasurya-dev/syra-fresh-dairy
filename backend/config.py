"""
SYRA Fresh - Configuration
Loads environment variables and defines app-wide settings.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/syra_fresh")
    DB_NAME = os.getenv("DB_NAME", "syra_fresh")

    # JWT Auth
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ADMIN_TOKEN_EXPIRES = timedelta(hours=12)

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://syra-fresh-dairy.vercel.app").split(",")

    # Razorpay (Test Mode)
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_XXXXXXXXXXXX")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "your_test_secret_here")

    # File uploads (product images)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Contact / Careers resume uploads
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
    MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB, enforced explicitly (stricter than the 8MB request-wide cap above)

    # Pagination defaults
    DEFAULT_PAGE_SIZE = 12
    MAX_PAGE_SIZE = 60

    # Delivery / business rules
    FREE_DELIVERY_THRESHOLD = 499
    DELIVERY_FEE = 40
    COD_ENABLED = True


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
