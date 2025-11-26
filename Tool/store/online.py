from flask import Blueprint, jsonify, request
from app.models import User, Store
from app.db import db
from flask_jwt_extended import jwt_required, get_jwt_identity

store = Blueprint('store', __name__)

@store.route('/create', methods=['POST'])
@jwt_required()
def create():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    data = request.get_json()
    store_name = data.get("store_name")
    logo_url = data.get("logo_url")
    cover_url = data.get("cover_url")
    store_description = data.get("store_description")

    if not store_name or not store_description:
        return jsonify({
            "message": "store name and store description required"
        }), 400
 