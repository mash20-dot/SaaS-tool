from flask import Blueprint, Response, send_file, jsonify
from openpyxl import Workbook
import io
from datetime import datetime
from app.models import db, User, Product, Payment
from flask_jwt_extended import get_jwt_identity, jwt_required


excel_export = Blueprint('excel_export', '__name__')


@excel_export.route("/export/excel", methods=['GET'])
@jwt_required()
def export_excel():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

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
    


    wb = Workbook()
    ws = wb.active
    ws.title = "product"


    # Add rows
    ws.append([
            "product_name",
            "selling_price",
            "initial_stock",
            "remaining_stock",
            "reorder_point",
            "expiration_date",
            "supplier_info"
        ])

        # Add rows from DB
    for product in products:
        ws.append([
            product.product_name,
            product.selling_price,
            product.initial_stock,
            product.remaining_stock,
            product.reorder_point,
            product.expiration_date if product.expiration_date else "",
            product.supplier_info if product.supplier_info else "",
            product.created_at.strftime("%Y-%m-%d") if product.created_at else "",
            product.status
        ])

    # Save to bytes buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="products.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
