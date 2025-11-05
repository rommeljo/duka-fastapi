from sqlalchemy import Integer, String, Float, Column, ForeignKey, DateTime
from datetime import datetime
from app.database import Base  # ✅ use the Base from database.py


class Products(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    productname = Column(String(100), nullable=False)
    productprice = Column(Float, nullable=False)
    stockquantity = Column(Integer, nullable=False)


class Sales(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    sale_date = Column(DateTime, default=datetime.utcnow, nullable=False)


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    phone = Column(String(15), nullable=True)


class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=False)
    phone_number = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="PENDING")
    checkout_request_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


