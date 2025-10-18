from flask import Blueprint,send_file, jsonify
from openpyxl import Workbook
import io
from datetime import datetime
from app.models import User, Product, Payment
from flask_jwt_extended import get_jwt_identity, jwt_required


excel_export = Blueprint('excel_export', '__name__')


@excel_export.route("/export/excel", methods=['GET'])
@jwt_required()
def export_excel():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "User not found"}), 400

    products = Product.query.filter_by(user_id=current_user.id).all()

    # Create workbook and sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Products"

    # Header row (fixed commas + consistent order)
    ws.append([
        "Product Name",
        "Selling Price",
        "Amount Spent",
        "Initial Stock",
        "Remaining Stock",
        "Reorder Point",
        "Expiration Date",
        "Supplier Info",
        "Date Created",
        "Status"
    ])

    # Add rows from database
    for product in products:
        ws.append([
            product.product_name,
            product.selling_price,
            product.amount_spent,
            product.initial_stock,
            product.remaining_stock,
            product.reorder_point,
            product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else "",
            product.supplier_info or "",
            product.created_at.strftime("%Y-%m-%d") if product.created_at else "",
            product.status or ""
        ])

    # Save to memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return file as attachment
    return send_file(
        output,
        as_attachment=True,
        download_name="products.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
