from flask import request, Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User
from app.db import db, app_logger 
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
import resend
from datetime import datetime, timedelta
import os
import threading
import time

security = Blueprint('security', '__name__')

# Validating email format
EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

resend.api_key = os.environ.get('RESEND_API_KEY')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://nkwabiz.com')

# def generate_verification_token():
#     return secrets.token_urlsafe(32)

# def send_verification_email(user_email, user_name, token):
#     # Use FRONTEND_URL instead of backend URL
#     verification_url = f"{FRONTEND_URL}/verify-email?token={token}"
#     
#     try:
#         params = {
#             "from": "info@nkwabiz.com",
#             "to": [user_email],
#             "subject": "Verify your email address",
#             "html": f"""
#                 <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
#                     <h2>Verify Your Email</h2>
#                     <p>Hi {user_name},</p>
#                     <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
#                     <a href="{verification_url}" 
#                        style="display: inline-block; padding: 12px 24px; background-color: #007bff; 
#                               color: white; text-decoration: none; border-radius: 4px; margin: 16px 0;">
#                         Verify Email
#                     </a>
#                     <p>Or copy and paste this link:</p>
#                     <p style="color: #666; word-break: break-all;">{verification_url}</p>
#                     <p>This link will expire in 24 hours.</p>
#                 </div>
#             """
#         }
#         
#         resend.Emails.send(params)
#         return True
#     except Exception as e:
#         print(f"Error sending verification email: {e}")
#         app_logger.log_error("Failed to send verification email", exception=e)
#         return False

def send_welcome_email(user_email, user_name, business_name):
    """Send welcome email to new user after successful signup"""
    try:
        params = {
            "from": "info@nkwabiz.com",
            "to": [user_email],
            "subject": f"Welcome to Nkwabiz, {user_name}!",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #007bff; margin-bottom: 10px;">🎉 Welcome to Nkwabiz!</h1>
                    </div>
                    
                    <p style="font-size: 16px;">Hi {user_name},</p>
                    
                    <p style="font-size: 16px; line-height: 1.6;">
                        Thank you for signing up with <strong>{business_name}</strong>! We're excited to have you on board.
                    </p>
                    
                    <p style="font-size: 16px; line-height: 1.6;">
                        You can now log in to your account and start managing your business operations with ease.
                    </p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #333;">Getting Started:</h3>
                        <ul style="line-height: 1.8; color: #555;">
                            <li>Set up your business profile</li>
                            <li>Add your products or services</li>
                            <li>Start managing your inventory</li>
                            <li>Track your sales and expenses</li>
                        </ul>
                    </div>
                    
                    <a href="{FRONTEND_URL}/login" 
                       style="display: inline-block; padding: 14px 28px; background-color: #007bff; 
                              color: white; text-decoration: none; border-radius: 6px; margin: 20px 0;
                              font-weight: bold;">
                        Log In to Your Account
                    </a>
                    
                    <p style="font-size: 14px; color: #666; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        If you have any questions or need assistance, feel free to reach out to us at 
                        <a href="mailto:info@nkwabiz.com" style="color: #007bff;">info@nkwabiz.com</a>
                    </p>
                    
                    <p style="font-size: 14px; color: #666;">
                        Best regards,<br>
                        <strong>The Nkwabiz Team</strong>
                    </p>
                </div>
            """
        }
        
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        app_logger.log_error("Failed to send welcome email", exception=e)
        return False

def send_welcome_email_delayed(user_email, user_name, business_name, delay_minutes=10):
    """Send welcome email after a delay"""
    def delayed_send():
        time.sleep(delay_minutes * 60)  # Convert minutes to seconds
        send_welcome_email(user_email, user_name, business_name)
    
    # Start the email sending in a background thread
    thread = threading.Thread(target=delayed_send)
    thread.daemon = True  # Thread will close when main program exits
    thread.start()

def send_admin_signup_notification(user_email, user_name, business_name, phone, location):
    """Send notification to admin when new user signs up"""
    try:
        params = {
            "from": "info@nkwabiz.com",
            "to": ["info@nkwabiz.com"],  
            "subject": f"New Signup: {business_name}",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>🎉 New User Signup</h2>
                    <p>A new user has registered on Nkwabiz:</p>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Name:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{user_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Business Name:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{business_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Email:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{user_email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Phone:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{phone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Location:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{location}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Signup Time:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</td>
                        </tr>
                    </table>
                    
                    <p style="margin-top: 20px; color: #666;">This is an automated notification from Nkwabiz.</p>
                </div>
            """
        }
        
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending admin notification: {e}")
        app_logger.log_error("Failed to send admin signup notification", exception=e)
        return False

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
        currency = data.get("currency")

        app_logger.log_auth_attempt(email, request.remote_addr)

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
            app_logger.log_auth_failure(email, reason="Empty fields")
            return jsonify({"message": f"{Missing_fields} required"}), 400
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({
                "message": "email already exist"
                }), 400
       
        if not re.match(EMAIL_REGEX, email):
            return jsonify({
                "message": "Invalid email format"
                }), 400
        
        hashed_password = generate_password_hash(password)
        
        # Generate verification token
        # verification_token = generate_verification_token()
        # token_expiry = datetime.utcnow() + timedelta(hours=24)
    
        save_user = User(
            firstname=firstname,
            lastname=lastname,
            business_name=business_name,
            email=email,
            phone=phone,
            location=location,
            currency=currency,
            password=hashed_password
            # is_verified=False,
            # verification_token=verification_token,
            # verification_token_expiry=token_expiry
        )

        
        
        db.session.add(save_user)
        db.session.commit()
        
        user_full_name = f"{firstname} {lastname}"

        # Send welcome email to user with 10 minute delay
        send_welcome_email_delayed(email, firstname, business_name, delay_minutes=10)

        # Send admin notification immediately
        send_admin_signup_notification(email, user_full_name, business_name, phone, location)
        

        # Send verification email
        # email_sent = send_verification_email(email, firstname, verification_token)
        
        # if not email_sent:
        #     app_logger.log_error("Verification email failed to send", context=f"User: {email}")
        
        
        app_logger.log_auth_success(email)
        
        return jsonify({
            "message": "Account created successfully! Check your email for a welcome message.",
            "email": email
        }), 201
    
    except Exception as e:
        db.session.rollback()
        app_logger.log_error("Signup failed", exception=e)
        return jsonify({"message": f"signup failed {str(e)}"}), 500


# @security.route('/verify-email', methods=['GET'])
# def verify_email():
#     token = request.args.get('token')
#     
#     if not token:
#         return jsonify({"message": "Token is required"}), 400
#     
#     
#     user = User.query.filter_by(verification_token=token).first()
#     
#     if not user:
#         return jsonify({
#             "message": "Invalid verification token"
#             }), 400
#     
#     if user.is_verified:
#         return jsonify({"message": "Email already verified"}), 200
#     
#     if user.verification_token_expiry < datetime.utcnow():
#         return jsonify({
#             "message": "Verification link has expired. Please request a new one."
#             }), 400
#     
#     # Verify user
#     user.is_verified = True
#     user.verification_token = None
#     user.verification_token_expiry = None
#     
#     try:
#         db.session.commit()
#         app_logger.log_auth_success(user.email, f"Email verified for {user.business_name}")
#         return jsonify({
#             "message": "Email verified successfully! You can now log in.",
#             "email": user.email
#         }), 200
#     except Exception as e:
#         db.session.rollback()
#         app_logger.log_error("Email verification failed", exception=e)
#         return jsonify({"message": "Verification failed"}), 500


# @security.route('/resend-verification', methods=['POST'])
# def resend_verification():
#     data = request.get_json()
#     email = data.get('email')
#     
#     if not email:
#         return jsonify({"message": "Email is required"}), 400
#     
#     user = User.query.filter_by(email=email).first()
#     
#     if not user:
#         return jsonify({"message": "User not found"}), 404
#     
#     if user.is_verified:
#         return jsonify({"message": "Email already verified"}), 400
#     
#     # Generate new token
#     user.verification_token = generate_verification_token()
#     user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
#     
#     try:
#         db.session.commit()
#         
#         # Send email
#         email_sent = send_verification_email(user.email, user.firstname, user.verification_token)
#         
#         if email_sent:
#             return jsonify({"message": "Verification email sent successfully"}), 200
#         else:
#             return jsonify({"message": "Failed to send verification email"}), 500
#             
#     except Exception as e:
#         db.session.rollback()
#         app_logger.log_error("Resend verification failed", exception=e)
#         return jsonify({"message": "Failed to resend verification"}), 500


@security.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({
                "message": "Email and password required"
                }), 400

        app_logger.log_auth_attempt(email, request.remote_addr)

        existing_user = User.query.filter_by(
            email=email).first()
        
        if not existing_user or not check_password_hash(existing_user.password, password):
            app_logger.log_auth_failure(email, reason="Invalid email or password")
            return jsonify({"message": "Invalid email or password"}), 400

        # if not existing_user.is_verified:
        #      return jsonify({
        #          "message": "Please verify your email before logging in"
        #          }), 403

        app_logger.log_auth_success(email, existing_user.business_name)
        access_token = create_access_token(identity=email)

        return jsonify({
            "message": "Logged in successfully",
            "access_token": access_token,
            "business_name": existing_user.business_name,
            # "is_verified": existing_user.is_verified
        }), 200

    except Exception as e:
        db.session.rollback()
        app_logger.log_error("Unexpected error during login", exception=e, context="login route")
        return jsonify({"message": "An unexpected error occurred. Please try again later."}), 500


@security.route('/reset/password', methods=['PUT'])
@jwt_required()
def reset():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400
    
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"message": "email required"}), 400
    
    if email != current_user.email:
        return jsonify({"message": "email not found"}), 400
    

@security.route("/user-info", methods=["GET", "OPTIONS"])
@jwt_required()
def user_info():
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200
    
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "email": user.email,
        "business_name": user.business_name,
        "role": user.role,
        "currency": user.currency,
        "firstname": user.firstname,
        "lastname": user.lastname,
        # "is_verified": user.is_verified
    }), 200