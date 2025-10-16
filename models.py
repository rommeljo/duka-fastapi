from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)

# Allow all origins (development use only)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://myduka_user:johnrommel@localhost:5432/store_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config["JWT_SECRET_KEY"] = "1234gh"

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# ==============================
# MODELS
# ==============================

class Products(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(100), nullable=False)
    productprice = db.Column(db.Float, nullable=False)
    stockquantity = db.Column(db.Integer, nullable=False)
    
    sales = db.relationship('Sales', backref='product', lazy=True)


class Sales(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    payments = db.relationship('Payment', backref='sale', lazy=True)


class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(15), nullable=True)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="PENDING")
    checkout_request_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==============================
# RUN
# ==============================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
    app.run(debug=True)
