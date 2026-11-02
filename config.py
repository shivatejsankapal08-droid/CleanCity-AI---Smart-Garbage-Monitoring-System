import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "cleancity_default_secret_key_change_me_99")
    DATABASE_PATH = BASE_DIR / "database" / "cleancity.db"
    
    # File upload directories
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads" / "complaints"
    PROOFS_FOLDER = BASE_DIR / "static" / "uploads" / "proofs"
    
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    
    # Gemini API configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    
    # Default Map Coordinates (Can be overridden by user location)
    DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "40.7128"))
    DEFAULT_LNG = float(os.getenv("DEFAULT_LNG", "-74.0060"))
    
    # Waste categories specification
    WASTE_CATEGORIES = [
        "Organic waste",
        "Plastic waste",
        "Paper waste",
        "Metal waste",
        "Mixed waste",
        "Other waste"
    ]
    
    # Severity levels
    SEVERITY_LEVELS = [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]
    
    # Status lifecycle
    STATUS_LIST = [
        "Pending",
        "Assigned",
        "In Progress",
        "Resolved",
        "Rejected"
    ]
