# mpesa.py
import os, base64, requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

BASE_URL = "https://sandbox.safaricom.co.ke"  # live: https://api.safaricom.co.ke

CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

TOKEN_URL = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
STK_URL = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

def _require_env():
    missing = []
    if not CONSUMER_KEY: missing.append("MPESA_CONSUMER_KEY")
    if not CONSUMER_SECRET: missing.append("MPESA_CONSUMER_SECRET")
    if not PASSKEY: missing.append("MPESA_PASSKEY")
    if not CALLBACK_URL: missing.append("MPESA_CALLBACK_URL")
    if missing:
        raise RuntimeError("Missing env vars: " + ", ".join(missing))

def normalize_ke_phone(phone: str) -> str:
    p = phone.strip().replace(" ", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0") and len(p) == 10:
        p = "254" + p[1:]
    return p  # should now be 2547XXXXXXXX

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")

def password(ts: str) -> str:
    raw = f"{SHORTCODE}{PASSKEY}{ts}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")

def access_token() -> str:
    _require_env()
    r = requests.get(TOKEN_URL, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def stk_push(amount: float, phone: str, account_ref: str, desc: str = "Duka Payment") -> dict:
    _require_env()
    ts = timestamp()
    token = access_token()
    msisdn = normalize_ke_phone(phone)

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password(ts),
        "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(round(amount)),
        "PartyA": msisdn,
        "PartyB": SHORTCODE,
        "PhoneNumber": msisdn,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": str(account_ref),
        "TransactionDesc": (desc or "Payment")[:13],
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(STK_URL, json=payload, headers=headers, timeout=30)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if not r.ok:
        raise RuntimeError(f"STK push failed HTTP {r.status_code}: {data}")

    return data


