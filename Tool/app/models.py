from db import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(250), nullable=False)
    lastname = db.Column(db.String(250), nullable=False)
    business_name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(300), unique=True, nullable=False)
    phone = db.Column(db.String(50), unique=True, nullable=False )
    location = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(400), nullable=False)