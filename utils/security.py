import hmac
import hashlib
from config import Config

def generate_delete_token(filename: str, timestamp: int) -> str:
    secret = Config.UPLOAD_TOKEN.encode()
    msg = f"{filename}:{timestamp}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()
