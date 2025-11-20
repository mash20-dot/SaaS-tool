from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app.models import User   # adjust to your project structure
from app.db import db
password = Blueprint('password', __name__)

@password.route("/update-password", methods=["POST"])
def update_password():
    data = request.get_json()

    email = data.get("email")
    new_password = data.get("new_password")

    if not email or not new_password:
        return jsonify({"error": "user_id and password are required"}), 400

   
    # Fetch user
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Update password safely
    hashed_password = generate_password_hash(new_password)
    user.password = hashed_password

    db.session.commit()

    return jsonify({"message": "Password updated successfully"})
