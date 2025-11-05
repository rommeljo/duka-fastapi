from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,OAuth2AuthorizationCodeBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from pwdlib import PasswordHash
from fastapi.middleware.cors import CORSMiddleware
from app.models import Products, Sales, Users, Payment
from app.database import SessionLocal
from app.jwt_service import create_access_token, get_current_active_user

app = FastAPI()
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ----------------------------
# Dependency for DB session
# ----------------------------



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)







def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Schemas
# ----------------------------
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
    phone: str | None = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

class Token(BaseModel):
    token: str

# ----------------------------
# Routes
# ----------------------------
@app.get("/")
def home():
    return {"Duka FastAPI": "1.0"}

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










@app.post("/register", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(Users).filter_by(email=user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user.password = password_hash.hash(user.password)
    new_user = Users(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token(new_user.email)
    return {"token": token}

@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(Users).all()


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Users).filter_by(email=form_data.username).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not password_hash.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Generate JWT token
    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=80, reload=False)
