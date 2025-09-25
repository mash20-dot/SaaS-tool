from flask import Blueprint, request, jsonify
from app.models import db, User, Product
from flask_jwt_extended import get_jwt_identity, jwt_required


stock_manage = Blueprint("stock_manage", "__name__")


@stock_manage.route('/stocks', methods=['POST'])
@jwt_required()
def stock():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message":
                "user not found"
        }), 400
    
    data = request.get_json()
    quantity = data.get("quantity")
    product_name = data.get("product_name")

    product = Product.query.filter_by(product_name=product_name).first()

    if not product:
        return {"error": "Product not found"}

    if product.remaining_stock < quantity:
        return {"error": "Not enough stock"}

    # deduct
    product.remaining_stock -= quantity
    db.session.commit()

    return {
        "message": f"Purchase successful, {quantity} deducted",
        "remaining_stock": product.remaining_stock
    }


@stock_manage.route('/stock/alert', methods=['POST', 'GET'])
@jwt_required()
def stock_alert():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message":
            "user not found"
        }), 400




    
    