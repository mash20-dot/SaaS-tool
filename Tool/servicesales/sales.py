from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.db import db
from app.models import User, Servicesales

servicesales = Blueprint('servicesales', __name__)

@servicesales.route('/sales', methods=['POST'])
@jwt_required()
def sales():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    data = request.get_json()
    client_name = data.get("client_name")
    date_time = data.get("date_time")
    income_received = data.get("income_received")
    payment_method = data.get("payment_method")
    notes = data.get("notes")

    Missing_fields = []

    if not income_received:
        Missing_fields.append("income_received")
        if Missing_fields:
            return jsonify({
                f"{Missing_fields} required"
            }), 400
        
    save_sales = Servicesales(
        client_name=client_name,
        date_time=date_time,
        income_received=income_received,
        payment_method=payment_method,
        notes=notes
    )
    db.session.add(save_sales)
    db.session.commit()
    return jsonify({
        "message": "service sales recorded successfully"
    }), 200

