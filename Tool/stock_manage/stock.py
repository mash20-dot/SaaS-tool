from flask import Blueprint, request, jsonify
from app.models import db, User, Product, SalesHistory
from flask_jwt_extended import get_jwt_identity, jwt_required


stock_manage = Blueprint("stock_manage", "__name__")

#route to enter stock to deduct
@stock_manage.route('/stocks', methods=['POST'])
@jwt_required()
def stock():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
                "user not found"
        }), 400
    
    data = request.get_json()
    quantity = data.get("quantity")
    product_name = data.get("product_name")

    product = Product.query.filter_by(
        product_name=product_name).first()
    
    
    if product.user_id != current_user.id:
            return jsonify({"message":
            "Unauthorized "
        }), 403

    if not product:
        return jsonify({"error":
             "Product not found"}), 404

    if product.remaining_stock < quantity:
        return jsonify({"error":
                 "Not enough stock"}), 400
    
    sales = SalesHistory(
        product_id=product.id,
        quantity=quantity, 
        unit_price=product.selling_price,
        total_price=product.selling_price*quantity


    )

    # deduct
    product.remaining_stock -= quantity
    db.session.add(sales)
    db.session.commit()

    return {
        "message": f"Purchase successful, {quantity} deducted",
        "remaining_stock": product.remaining_stock
    }


@stock_manage.route('/stock/alert', methods=['POST', 'GET'])
@jwt_required()
def stock_alert():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
            "user not found"
        }), 400
    
    products = Product.query.filter_by(
         user_id=current_user.id).all()
    

    notification = []
    for pro in products:
        if pro.remaining_stock <= pro.reorder_point:
         notification.append({
              "product_name":pro.product_name,
              "remaining_stock":pro.remaining_stock,
              "message":
                f"Low stock! Reoder {pro.product_name}"
         })
    return jsonify({"alert": notification}),200


@stock_manage.route('/stocks/history', methods=['GET'])
@jwt_required()
def history():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()
    
    if not current_user:
        return jsonify({"message":
            "user not found"
        }), 400
    
    get_history = db.session.query(
        SalesHistory, Product).join(Product).all()
    
    result = []
    for sale, product in get_history:
        result.append({
            "sale_id": sale.id,
            "product_name": product.product_name, 
            "quantity": sale.quantity,
            "unit_price":sale.unit_price,
            "total_price":sale.total_price,
            "date": sale.created_at
        })

    return jsonify(result), 200
   



    
    