import hmac
import hashlib
import json
import os
from config import Config

def generate_delete_token(filename: str, timestamp: int) -> str:
    secret = Config.MASTER_KEY.encode() if Config.MASTER_KEY else b"default_secret"
    msg = f"{filename}:{timestamp}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()

def get_valid_tokens() -> dict:
    tokens = {}
    if Config.MASTER_KEY and Config.MASTER_KEY != "SUPER_SECRET_MASTER_KEY_HERE":
        tokens[Config.MASTER_KEY] = "admin"
        
    if os.path.exists(Config.USERS_FILE):
        try:
            with open(Config.USERS_FILE, 'r') as f:
                users = json.load(f)
                for username, token in users.items():
                    tokens[token] = username
        except Exception:
            pass
            
    return tokens

def is_valid_token(token: str) -> bool:
    tokens = get_valid_tokens()
    for valid_token in tokens.keys():
        if hmac.compare_digest(token, valid_token):
            return True
    return False

def get_username_from_token(token: str) -> str:
    tokens = get_valid_tokens()
    for valid_token, username in tokens.items():
        if hmac.compare_digest(token, valid_token):
            return username
    return "anonymous"
