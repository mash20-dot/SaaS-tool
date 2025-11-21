from flask import Blueprint, request, jsonify
from app.models import User
from app.db import db
from datetime import datetime, timedelta
import resend
import secrets
import os
from werkzeug.security import generate_password_hash

forgotpassword = Blueprint('forgotpassword', __name__)

resend.api_key = os.getenv('RESEND_API_KEY')


# ------------------------------
# FORGOT PASSWORD (ALLOW OPTIONS)
# ------------------------------
@forgotpassword.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200

    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email not found"}), 404

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    user.reset_token = token
    user.reset_expires = expires_at
    db.session.commit()

   # reset_link = f"https://nkwabiz.com/reset-password?token={token}"
    reset_link = f"https://nkwabiz-frontend-1.onrender.com/reset-password?token={token}"

    resend.Emails.send({
        "from": "Nkwabiz <info@nkwabiz.com>",
        "to": email,
        "subject": "Reset Your Password",
        "html": f"""
            <h2>Password Reset</h2>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_link}">Reset Password</a>
        """
    })

    return jsonify({"message": "Password reset email sent!"}), 200


# ------------------------------
# RESET PASSWORD (ALLOW OPTIONS)
# ------------------------------
@forgotpassword.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200

    data = request.get_json()
    token = data.get("token")
    password = data.get("password")

    if not password:
        return jsonify({"error": "New password is required"}), 400

    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return jsonify({"error": "Invalid or expired reset token"}), 400

    if user.reset_expires < datetime.utcnow():
        return jsonify({"error": "Reset token has expired"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    user.password = generate_password_hash(password)
    user.reset_token = None
    user.reset_expires = None
    db.session.commit()

    return jsonify({"message": "Password successfully reset"}), 200
