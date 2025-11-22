from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import User

def role_required(*allowed_roles):
    #the route being protected
    def wrapper(fn):
        #making sure the function keeps its original identity
        @wraps(fn)
        #accepting any kind of input in the decorated function
        def decorated(*args, **kwargs):

            # Allow OPTIONS (CORS preflight)
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)

            # Verify JWT first
            verify_jwt_in_request()
            current_email = get_jwt_identity()

            current_user = User.query.filter_by(email=current_email).first()

            if not current_user:
                return jsonify({"message": "User not found"}), 404

            if not current_user or current_user.role not in allowed_roles:
                return jsonify({"message": "Access denied"}), 403

            return fn(*args, **kwargs)
        return decorated
    return wrapper