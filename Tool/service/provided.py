from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.db import db
from app.models import User, Services


service = Blueprint('service', __name__)


@service.route('/provide', methods=['POST'])
@jwt_required()
def provide():

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
        service_name = data.get("services")
        description = data.get("description")
        pricing_type = data.get("pricing_type")
        price = data.get("price")

        Missing_fields = []

        if not service_name:
            Missing_fields.append("service_name")
        if not description:
            Missing_fields.append("description")
            if Missing_fields:
                return jsonify({
                    "message": f"{Missing_fields} required"
                }), 400
            
        save_services = Services(
            user_id=current_user.id,
            service_name=service_name,
            description=description,
            pricing_type=pricing_type,
            price=price
        )

        db.session.add(save_services)
        db.session.commit()
        return jsonify({
            "message": "services added successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
           "status": "Error", "message":str(e)
        }), 500
    
@service.route('/see/all', methods=['GET'])
@jwt_required()
def see_all():

    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(
            email=current_email
        ).first()

        if not current_user:
            return jsonify({
                "message": "user not found"
            }), 400
        
        all_services = Services.query.filter_by(
            user_id=current_user.id
        ).all()

        serve = []

        for me in all_services:
            serve.append({
                "message":"services retrieved successfully",
                "user_id":current_user.id,
                "service_name":me.service_name,
                "description":me.description,
                "pricing_type":me.pricing_type,
                "price":me.price

            })
        return jsonify(serve), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error", "message":str(e)
        }), 500


            