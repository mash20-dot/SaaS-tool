from flask import request, Blueprint, jsonify
from app.models import User, Product
from flask_jwt_extended import get_jwt_identity, jwt_required


dashboard = Blueprint('dashboard', '__name__')

@dashboard.route('/board', methods=['GET'])
@jwt_required()
def board():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
            "user not found"
        }), 400
    
    all_pro = Product.query.filter_by(
         user_id=current_user.id).all()
    
    all_info = []
    for me in  all_pro:
        all_info.append({
            "business_name": current_user.business_name,
            "product_name":me.product_name,
            "selling_price":float(me.selling_price),
            "amount_spent":float(me.amount_spent),
            "initial_stock":me.initial_stock,
            "expiration_date":me.expiration_date,
            "remaining_stock":me.remaining_stock,
            "supplier_info":me.supplier_info,
            "balance": float(current_user.sms_balance) if current_user.sms_balance is not None else 0.0
        })

    return jsonify(all_info), 200
    

    

