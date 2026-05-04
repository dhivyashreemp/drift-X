import hashlib
import hmac
import secrets
import json
import base64
import time
import os

JWT_SECRET = os.getenv("JWT_SECRET", "driftx-dev-secret-change-in-production")
TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split("$", 1)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return hmac.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


def create_token(email: str) -> str:
    payload = json.dumps({"email": email, "exp": time.time() + TOKEN_EXPIRY_SECONDS})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> str | None:
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        if payload["exp"] < time.time():
            return None
        return payload["email"]
    except Exception:
        return None
