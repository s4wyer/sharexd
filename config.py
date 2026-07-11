import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 100)) * 1024 * 1024
    
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
    S3_REGION = os.environ.get("S3_REGION", "us-east-1")
    
    USERS_FILE = os.environ.get("USERS_FILE", "users.json")
    MASTER_KEY = os.environ.get("MASTER_KEY", "SUPER_SECRET_MASTER_KEY_HERE")
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback_secret_for_sessions_replace_me")
    
    ABUSE_EMAIL = os.environ.get("ABUSE_EMAIL", "abuse@yourdomain.com")
    ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "your_handle")
    GITHUB_URL = os.environ.get("GITHUB_URL", "https://github.com/s4wyer/sharexd")

    DONATION_URL = os.environ.get("DONATION_URL")
    DONATION_PLATFORM = os.environ.get("DONATION_PLATFORM")
    
    TARPIT_ENABLED = str(os.environ.get("TARPIT_ENABLED", "true")).lower() in ("true", "1", "yes", "t")
    
    VERSION = "v1.2.7"
