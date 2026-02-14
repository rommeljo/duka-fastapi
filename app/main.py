from pathlib import Path
from dotenv import load_dotenv

# ----------------------------
# Load .env FIRST (before importing env-dependent modules)
# ----------------------------
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from pwdlib import PasswordHash

from app.database import SessionLocal, Base, engine
from app.models import Products, Sales, Users, Payment, OTP
from app.jwt_service import create_access_token, get_current_active_user, get_current_user

from app.otp_service import generate_4_digit, hash_otp, expires_in
from app.sms_service import send_sms
from app.email_service import send_email_with_pdf
from app.receipt_pdf import build_receipt_pdf
# IMPORTANT: if your file is utils.py, change this import:
from app.utilis import normalize_ke_phone

from app.mpesa import stk_push

# ----------------------------
# App
# ----------------------------
app = FastAPI()
print("✅ LOADED app/main.py")

# ----------------------------
# CORS (DEV)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ----------------------------
# DB dependency
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Schemas
# ----------------------------
class ForgotPasswordBody(BaseModel):
    phone: str

class VerifyBody(BaseModel):
    otp: str

class ResetBody(BaseModel):
    user_id: int
    otp: str
    new_password: str

class StkPushRequest(BaseModel):
    sale_id: int

class ProductData(BaseModel):
    productname: str
    productprice: float
    stockquantity: int

class ProductDataResponse(ProductData):
    id: int

class SaleData(BaseModel):
    product_id: int
    quantity: int

class SaleDataResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    sale_date: datetime
    productname: str
    productprice: float

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str  # required

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str

class Token(BaseModel):
    token: str

# ----------------------------
# Health check (debug CORS)
# ----------------------------
@app.get("/__ping")
def ping():
    return {"ok": True, "where": "app/main.py"}

# ----------------------------
# Basic
# ----------------------------
@app.get("/")
def home():
    return {"Duka FastAPI": "1.0"}

# ----------------------------
# Products
# ----------------------------
@app.get("/products", response_model=list[ProductDataResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(Products).all()

@app.post("/products", response_model=ProductDataResponse)
def add_product(
    prod: ProductData,
    user: str = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_prod = Products(**prod.dict())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod

# ----------------------------
# Sales
# ----------------------------
@app.post("/sales", response_model=SaleDataResponse)
def add_sale(sale: SaleData, db: Session = Depends(get_db)):
    product = db.query(Products).filter_by(id=sale.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if sale.quantity > product.stockquantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    product.stockquantity -= sale.quantity
    new_sale = Sales(product_id=sale.product_id, quantity=sale.quantity)
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)

    return SaleDataResponse(
        id=new_sale.id,
        product_id=new_sale.product_id,
        quantity=new_sale.quantity,
        sale_date=new_sale.sale_date,
        productname=product.productname,
        productprice=product.productprice
    )

@app.get("/sales", response_model=list[SaleDataResponse])
def get_sales(
    user: str = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sales = db.query(Sales).all()
    results = []
    for sale in sales:
        product = db.query(Products).filter_by(id=sale.product_id).first()
        if product:
            results.append(
                SaleDataResponse(
                    id=sale.id,
                    product_id=sale.product_id,
                    quantity=sale.quantity,
                    sale_date=sale.sale_date,
                    productname=product.productname,
                    productprice=product.productprice,
                )
            )
    return results

# ----------------------------
# Auth
# ----------------------------
@app.post("/register", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(Users).filter_by(email=user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    phone_norm = normalize_ke_phone(user.phone)

    # enforce unique phone
    if db.query(Users).filter_by(phone=phone_norm).first():
        raise HTTPException(status_code=400, detail="Phone already exists")

    new_user = Users(
        name=user.name,
        email=user.email,
        password=password_hash.hash(user.password),
        phone=phone_norm
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.email)
    return {"token": token}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Users).filter_by(email=form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not password_hash.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}

# ----------------------------
# Mpesa STK
# ----------------------------
@app.post("/payments/stkpush")
def start_stk_push(
    body: StkPushRequest,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_user = db.query(Users).filter_by(email=email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail=f"User not found for email: {email}")

    if not db_user.phone:
        raise HTTPException(status_code=400, detail="User has no phone number saved.")

    sale = db.query(Sales).filter_by(id=body.sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    product = db.query(Products).filter_by(id=sale.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product for this sale not found")

    amount = float(sale.quantity) * float(product.productprice)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    payment = Payment(
        sale_id=sale.id,
        phone_number=db_user.phone,
        amount=amount,
        status="PENDING"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    try:
        res = stk_push(
            amount=amount,
            phone=db_user.phone,
            account_ref=str(payment.id),
            desc=f"Sale {sale.id}"
        )
    except Exception as e:
        payment.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Mpesa STK push failed: {e}")

    checkout_id = res.get("CheckoutRequestID")
    if not checkout_id:
        payment.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"No CheckoutRequestID returned: {res}")

    payment.checkout_request_id = checkout_id
    db.commit()

    return {
        "message": "STK Push initiated. Check phone and enter PIN.",
        "payment_id": payment.id,
        "checkout_request_id": checkout_id
    }

@app.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    print("MPESA CALLBACK:", payload)

    stk = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc")

    if not checkout_id:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    payment = db.query(Payment).filter_by(checkout_request_id=checkout_id).first()
    if not payment:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # Pull Mpesa receipt number if provided
    mpesa_receipt = None
    for item in stk.get("CallbackMetadata", {}).get("Item", []) or []:
        if item.get("Name") == "MpesaReceiptNumber":
            mpesa_receipt = item.get("Value")

    if result_code == 0:
        payment.status = "SUCCESS"
        db.commit()

        user = db.query(Users).filter_by(phone=payment.phone_number).first()
        sale = db.query(Sales).filter_by(id=payment.sale_id).first()

        # Only email if we have user + email
        if user and user.email:
            receipt_no = f"DUKA-{payment.id}"
            pdf_bytes = build_receipt_pdf(
                shop_name="Duka Shop",
                receipt_no=receipt_no,
                customer_name=user.name,
                customer_email=user.email,
                amount=payment.amount,
                status="SUCCESS",
                sale_id=payment.sale_id,
                phone=payment.phone_number,
                mpesa_receipt=mpesa_receipt,
            )

            send_email_with_pdf(
                to_email=user.email,
                subject="Your Duka receipt (PDF)",
                body=(
                    f"Hi {user.name},\n\n"
                    f"Payment received successfully.\n"
                    f"Amount: KES {payment.amount:,.2f}\n"
                    f"Receipt: {receipt_no}\n"
                    f"{'Mpesa: ' + mpesa_receipt if mpesa_receipt else ''}\n\n"
                    f"Receipt PDF is attached.\n"
                ),
                pdf_bytes=pdf_bytes,
                filename=f"{receipt_no}.pdf"
            )

    else:
        payment.status = "FAILED"
        db.commit()
        print("Payment failed:", result_desc)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.get("/payments/{payment_id}")
def get_payment_status(
    payment_id: int,
    user_email: str = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    p = db.query(Payment).filter_by(id=payment_id).first()
    if not p:
        raise HTTPException(404, "Payment not found")
    return p

# ----------------------------
# Forgot password (OTP flow)
# ----------------------------
@app.post("/forgot-password")
def forgot_password(body: ForgotPasswordBody, db: Session = Depends(get_db)):
    print("1) forgot-password hit")

    phone = normalize_ke_phone(body.phone)
    print("2) phone normalized:", phone)

    user = db.query(Users).filter_by(phone=phone).first()
    print("3) user found:", bool(user))

    # Avoid account enumeration
    if not user:
        return {"message": "If the phone exists, an OTP has been sent."}

    code = generate_4_digit()
    print("4) otp generated:", code)

    otp_row = OTP(
        user_id=user.id,
        otp_hash=hash_otp(code, str(user.id)),
        purpose="RESET_PASSWORD",
        expires_at=expires_in(5),
        used=False,
        last_sent_at=datetime.now(timezone.utc)
    )
    db.add(otp_row)
    db.commit()
    print("5) otp saved to db")

    # Send SMS (REAL)
    try:
        resp = send_sms(
            phone=user.phone,  # sms_service will add + automatically now
            message=f"Your reset code is {code}. Expires in 5 minutes."
        )
        print("✅ AT response:", resp)
    except Exception as e:
        print("❌ SMS failed:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "If the phone exists, an OTP has been sent.", "user_id": user.id}



@app.post("/reset-password")
def reset_password(body: ResetBody, db: Session = Depends(get_db)):
    user = db.query(Users).filter_by(id=body.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    row = (
        db.query(OTP)
        .filter_by(user_id=body.user_id, purpose="RESET_PASSWORD", used=False)
        .order_by(OTP.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(400, "Invalid or expired code")

    if datetime.now(timezone.utc) > row.expires_at:
        raise HTTPException(400, "Invalid or expired code")

    if row.otp_hash != hash_otp(body.otp.strip(), str(body.user_id)):
        row.attempts += 1
        db.commit()
        raise HTTPException(400, "Invalid or expired code")

    row.used = True
    user.password = password_hash.hash(body.new_password)
    db.commit()

    return {"message": "Password updated"}

# ----------------------------
# Startup
# ----------------------------
@app.on_event("startup")
def on_startup():
    print("✅ Creating tables")
    Base.metadata.create_all(bind=engine)
