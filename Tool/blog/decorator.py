from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import User

def role_required(*allowed_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):

            # Allow OPTIONS (CORS preflight) WITHOUT running fn
            if request.method == "OPTIONS":
                return jsonify({"message": "OK"}), 200

            # Verify JWT first
            verify_jwt_in_request()
            current_email = get_jwt_identity()

            current_user = User.query.filter_by(email=current_email).first()

            if not current_user:
                return jsonify({"message": "User not found"}), 404

            if current_user.role not in allowed_roles:
                return jsonify({"message": "Access denied"}), 403

            return fn(*args, **kwargs)

        return decorated
    return wrapper
