from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
from app.models import User

sms = Blueprint("sms", "__name__")

@sms.route('/api/sms/send', methods=['POST'])
@jwt_required()
def send():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    
