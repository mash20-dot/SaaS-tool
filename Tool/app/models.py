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
    expiration_date = db.Column(db.String(250), nullable=False)
    supplier_info = db.Column(db.String(1000))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    archived_at = db.Column(db.DateTime)


