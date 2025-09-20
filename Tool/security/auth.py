from flask import request, Blueprint, jsonify
from app.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
import re

security = Blueprint('security', '__name__')

#validating email format
EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'


@security.route('/signup', methods=['POST'])
def signup():

    try:
        data = request.get_json()
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")
        phone = data.get("phone")
        location = data.get("location")
        password = data.get("password")



        Missing_fields = []

        if not firstname:
            Missing_fields.append("firstname")
        if not lastname:
            Missing_fields.append("lastname")
        if not email:
            Missing_fields.append("email")
        if not phone:
            Missing_fields.append("phone")
        if not location:
            Missing_fields.append("location")
        if not password:
            Missing_fields.append("password")
            if Missing_fields:
                return jsonify({"message":
                 f"{Missing_fields} required"}), 400
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({
                "message":
                "email already exist"
            }), 400
       
        if not re.match(EMAIL_REGEX, email):
            return jsonify({"message":
                 "Invalid email format"}), 400
        
        hashed_password = generate_password_hash(password)
        
        save_user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            phone=phone,
            location=location,
            password=hashed_password
        )

        db.session.add(save_user)
        db.session.commit()
        return jsonify({
            "message": "Account created successfullly"
            }),201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message":
            f"signup failed {str(e)}"
    }), 500
