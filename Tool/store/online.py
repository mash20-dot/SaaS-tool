from flask import Blueprint, jsonify, request
from app.models import User, Store
from app.db import db
from flask_jwt_extended import jwt_required, get_jwt_identity
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

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
    profile_picture = data.get("profile_picture")
    cover_photo = data.get("cover_photo")
    store_description = data.get("store_description")

    if not store_name or not store_description:
        return jsonify({
            "message": "store name and store description required"
        }), 400
    


@store.route('/store/<slug>/upload-logo', methods=['POST'])
@jwt_required()
def upload_store_logo(slug):

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    available_store = Store.query.filter_by(slug=slug).first()
    if not available_store:
        return {"error": "Store not found"}, 404

    image = request.files.get('image')
    if not image:
        return {"error": "No image provided"}, 400

    # Upload to cloudinary
    result = cloudinary.uploader.upload(image)
    available_store.logo_url = result["secure_url"] 

    db.session.commit()

    return {
        "message": "Logo uploaded successfully",
        "logo_url": available_store.logo_url
    }



@store.route('/store/<slug>/upload-banner-logo', methods=['POST'])
@jwt_required()
def upload_banner(slug):

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    available_store = Store.query.filter_by(
        slug=slug
    ).first()

    if not available_store:
        return jsonify({
            "message": "store not found"
        }), 400
    
    image = request.files.get("image")
    if not image:
        return jsonify({
            "message": "no image provided"
        }), 400
    
    result = cloudinary.uploader.upload(image)
    available_store.banner_url = result["secure_url"]
    
    db.session.commit()

    return {
        "message": "banner uploaded successfully",
        "banner_url": available_store.banner_url
    }

