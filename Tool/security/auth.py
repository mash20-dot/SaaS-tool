from flask import request, Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User
from app.db import db, app_logger 
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
        business_name = data.get("business_name")
        email = data.get("email")
        phone = data.get("phone")
        location = data.get("location")
        password = data.get("password")



         # Log the attempt
        app_logger.sign_auth_attempt(email, request.remote_addr)

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
        if not business_name:
            Missing_fields.append("business_name")
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
        app_logger.sign_auth_failure(email, reason="Empty fields")
        
        hashed_password = generate_password_hash(password)
        
        save_user = User(
            firstname=firstname,
            lastname=lastname,
            business_name=business_name,
            email=email,
            phone=phone,
            location=location,
            password=hashed_password
        )

         # Success
        app_logger.sign_auth_success(email)

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


@security.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400

        # Log the attempt
        app_logger.log_auth_attempt(email, request.remote_addr)

        existing_user = User.query.filter_by(
            email=email).first()
        

        if not existing_user or not check_password_hash(
            existing_user.password, password):
           
            app_logger.log_auth_failure(
                email, reason="Invalid email or password")
           
            return jsonify({"message":
                 "Invalid email or password"}), 400

        # Success
        app_logger.log_auth_success(email, existing_user.business_name)
        access_token = create_access_token(identity=email)

        return jsonify({
            "message": "Logged in successfully",
            "access_token": access_token,
            "business_name": existing_user.business_name
        }), 200

    except Exception as e:
        db.session.rollback()
        app_logger.log_error(
            "Unexpected error during login",
              exception=e,
                context="login route")
        
        return jsonify({"message":
             "An unexpected error occurred. Please try again later."}), 500


@security.route('/reset/password', methods=['PUT'])
@jwt_required()
def reset():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({
            "message":"email required"
        }), 400
    
    if email != current_user.email:
        return jsonify({
            "message": "email not found"
        }), 400