import os
import requests

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY")
AT_ENV = (os.getenv("AT_ENV") or "sandbox").lower()  # sandbox | live

def send_sms(phone: str, message: str):
    if not AT_API_KEY:
        raise RuntimeError("AT_API_KEY missing in environment (.env).")

    to_phone = phone.strip()
    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone  # +2547...

    url = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if AT_ENV == "sandbox"
        else "https://api.africastalking.com/version1/messaging"
    )

    # IMPORTANT: ignore hidden Windows/system proxy settings
    s = requests.Session()
    s.trust_env = False

    headers = {
        "ApiKey": AT_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "username": AT_USERNAME,  # sandbox must be "sandbox"
        "to": to_phone,
        "message": message,
    }

    r = s.post(url, headers=headers, data=data, timeout=30)

    # Try decode response
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}

    if not r.ok:
        raise RuntimeError(f"AT SMS HTTP {r.status_code}: {payload}")

    return payload
