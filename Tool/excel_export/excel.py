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

    if premium.expiry_date < datetime.utcnow():
        return jsonify({"message": 
            "Your premium has expired. Please renew."}), 403

    if not premium:
        return jsonify({"message":
         "You do not have a premium subscription. Please upgrade."}), 403

    


    products = Product.query.filter_by(
        user_id=current_user.id).all()
    


    wb = Workbook()
    ws = wb.active
    ws.title = "product"

    # Add headers
    ws.append(["Name", "Email"])

    # Add rows
    for product in products:
        ws.append([
            "product_name",
            "selling_price",
            "initial_stock",
            "remaining_stock",
            "reorder_point",
            "expiration_date",
            "supplier_info",
            "user_id",
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
