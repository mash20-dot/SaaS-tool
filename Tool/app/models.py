from db import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(250), nullable=False)
    lastname = db.Column(db.String(250), nullable=False)
    business_name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(300), unique=True, nullable=False)
    phone = db.Column(db.String(50), unique=True, nullable=False )
    location = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(400), nullable=False)
    products = db.relationship('Product', backref='user', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class Product(db.Model):
    #__tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(250), nullable=False)
    selling_price = db.Column(db.String(250), nullable=False)
    initial_stock = db.Column(db.Integer, nullable=False)
    remaining_stock = db.Column(db.Integer, nullable=False)
    reorder_point = db.Column(db.Integer, default=10)
    expiration_date = db.Column(db.String(250), nullable=True)
    supplier_info = db.Column(db.String(1000))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    archived_at = db.Column(db.DateTime)
     # relationship to sales
    sales = db.relationship("SalesHistory", back_populates="product", cascade="all, delete-orphan")

class SalesHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    # relationship back to product
    product = db.relationship("Product", back_populates="sales")


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Amount in kobo (Paystack uses kobo, so 1000 = ₦10.00)
    amount = db.Column(db.Integer, nullable=False)
    
    # Paystack reference (very important for verification)
    reference = db.Column(db.String(200), unique=True, nullable=False)
    
    # Payment status: pending, success, failed
    status = db.Column(db.String(50), default="pending", nullable=False)

    currency = db.Column(db.String(50), default="GHS", nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



