import secrets, hashlib
from datetime import datetime, timedelta, timezone

def generate_4_digit() -> str:
    return f"{secrets.randbelow(10000):04d}"

def hash_otp(code: str, salt: str) -> str:
    # salt can be user_id or server secret
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()

def expires_in(minutes=5):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
