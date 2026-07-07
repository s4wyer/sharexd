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
    MASTER_KEY = os.environ.get("MASTER_KEY", "default_insecure_master_key")
    
    ABUSE_EMAIL = os.environ.get("ABUSE_EMAIL", "abuse@yourdomain.com")
    ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "your_handle")
    GITHUB_URL = os.environ.get("GITHUB_URL", "https://github.com/s4wyer/sharexd")
    
    VERSION = "v1.1.3"
