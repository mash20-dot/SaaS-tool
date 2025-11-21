from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
password = Blueprint('password', __name__)

@password.route("/update-password", methods=["POST"])
@jwt_required()
def update_password():

    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(
            email=current_email
        ).first()

        if not current_user:
            return jsonify({
                "message": "user not found"
            }), 400

        data = request.get_json()


        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            return jsonify({
                "error": "old_password and new_password are required"
                }), 400

        if len(new_password) < 8:
            return jsonify({
                "error": "Password must be at least 8 characters"
                }), 400

        
        if not check_password_hash(current_user.password, old_password):
            return jsonify({
                "message": "Old password is incorrect"
                }), 400 # Password validation
        
        
    
        # Update password safely
        hashed_password = generate_password_hash(new_password)
        current_user.password = hashed_password

        db.session.commit()

        return jsonify({"message": "Password updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": str(e)
        }), 500
