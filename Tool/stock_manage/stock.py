from flask import Blueprint, request, jsonify
from app.models import User, Product, SalesHistory, Payment
from app.db import db
from flask_jwt_extended import get_jwt_identity, jwt_required
from datetime import datetime

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
    quantity = int(data.get("quantity"))
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
        total_price=product.selling_price*quantity,
        profit=(product.selling_price - product.amount_spent)*quantity
#return the sum of all sales money with the latest date
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
    
    premium = Payment.query.filter_by(
        user_id=current_user.id, status="success"
    ).order_by(Payment.created_at.desc()).first()

    if not premium:
        return jsonify({"message":
         "You do not have a premium subscription. Please upgrade."}), 403

    if premium.expiry_date < datetime.utcnow():
        return jsonify({"message": 
        "Your premium has expired. Please renew."}), 403

    
   
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



#route to view sales analytics and history
@stock_manage.route('/stocks/history', methods=['GET'])
@jwt_required()
def history():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message": "User not found"}), 400

    premium = Payment.query.filter_by(
        user_id=current_user.id, status="success"
    ).order_by(Payment.created_at.desc()).first()

    if not premium:
        return jsonify({"message":
         "You do not have a premium subscription. Please upgrade."}), 403

    if premium.expiry_date < datetime.utcnow():
        return jsonify({"message":
             "Your premium has expired. Please renew."}), 403

    # Fetch all sales history joined with Product
    get_history = (
        db.session.query(SalesHistory, Product)
        .join(Product)
        .filter(Product.user_id == current_user.id)
        .all()
    )

    if not get_history:
        return jsonify({"message":
                 "No sales history found"}), 404

    result = []
    for sale, product in get_history:
        result.append({
            "sale_id": sale.id,
            "product_name": product.product_name,
            "quantity": sale.quantity,
            "unit_price": sale.unit_price,
            "total_price": sale.total_price,
            "profit": sale.profit,
            "date": sale.created_at
        })

    # Get total profit and total sales for the most recent date
    sale_dates = [sale.created_at.date() for sale, _ in get_history]
    most_recent_date = max(sale_dates)

    # Filter sales for that date
    sales_for_recent_date = [
        sale for sale, _ in get_history
        if sale.created_at.date() == most_recent_date
    ]

    # Compute totals
    total_profit_today = sum(sale.profit for sale in sales_for_recent_date)
    total_sales_today = sum(sale.total_price for sale in sales_for_recent_date)

    return jsonify({
        "sales_history": result,
        "summary": {
            "recent_date": most_recent_date.isoformat(),
            "total_sales_for_recent_date": total_sales_today,
            "total_profit_for_recent_date": total_profit_today
        }
    }), 200

#route to get product sold, for free users
@stock_manage.route('/product/sold', methods=['GET'])
@jwt_required()
def sold():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400

    get_history = (
        db.session.query(SalesHistory, Product)
        .join(Product)
        .filter(Product.user_id == current_user.id)
        .all()
    )

    results = []
    for sale, product in get_history:
        results.append({
            "product_name": product.product_name,
            "quantity": sale.quantity,
            "total_price": sale.total_price,
            "date": sale.created_at
        })

    return jsonify(results), 200
