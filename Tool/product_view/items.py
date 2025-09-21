from flask import request, Blueprint, jsonify
from app.models import db, User, Product
from flask_jwt_extended import get_jwt_identity, jwt_required


product_view = Blueprint('product_view', '__name__')

@product_view.route('/start', methods=['POST'])
@jwt_required()
def start():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message":
                "user not found"
    }), 400

    data = request.get_json()
    product_name = data.get("product_name")
    selling_price = data.get("selling_price")
    initial_stock = data.get("initial_stock")
    expiration_date = data.get("expiration_date")
    supplier_info = data.get("supplier_info")

    Missing_fields = []
    if not product_name:
        Missing_fields.append("product_name")
    if not selling_price:
        Missing_fields.append("selling_price")
    if not initial_stock:
        Missing_fields.append("initial_stock")
    if not expiration_date:
        Missing_fields.append("expiration_date")
    if not supplier_info:
        Missing_fields.append("supplier_info")
        if Missing_fields:
            return jsonify({"message":
            f"{Missing_fields} required"
        }), 400

    save_pro = Product(
        product_name=product_name,
        sellinga_price=selling_price,
        initial_stock=initial_stock,
        expiration_date=expiration_date,
        supplier_info=supplier_info
    )
    db.session.add(save_pro)
    db.session.commit()
    return jsonify({"message":
        "product information saves successfully"
                    
    }), 200

@product_view.route('/get_products', methods=['GET'])
@jwt_required()
def get_products():
    
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()
    if not current_user:
        return jsonify({"message":
            "user not found"
    }), 400

    get_all = Product.query.all()

    pro = []
    for me in get_all:
        pro.append({
            "product_name":me.product_name,
            "selling_price":me.selling_price,
            "initial_stock":me.initial_stock,
            "expiration_date":me.expiration_date,
            "supplier_info":me.supplier_info

        }), 200
        return jsonify(pro)
    
@product_view.route('/filter', methods=['GET'])
@jwt_required()
def filter():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()
    if not current_user:
        return jsonify({"message":
            "user not found"
    }), 400

    data = request.get_json()
    product_name = data.get("product_name")

    filter_pro = Product.query.filter_by(product_name=product_name).first()
    if not filter_pro:
        return jsonify({"message":
            "product not found"
    }), 400

    pro = []
    for me in filter_pro:
        pro.append({
            "product_name":me.product_name,
            "selling_price": me.selling_price,
            "initial_stock":me.initial_stock,
            "expiration_date":me.expiration_date,
            "supplier_info":me.supplier_info
    }), 200
        
@product_view.route('/product/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        current_user_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_user_email).first()
        
        if not current_user:
            return jsonify({"message": "User not found"}), 404
        
        product = Product.query.get_or_404(product_id)
        
        if product.user_id != current_user.id:
            return jsonify({"message": "Unauthorized to edit this product"}), 403
        
        data = request.get_json()
        updated_fields = []
        
        # Only update fields that are actually provided and not empty
        if data.get('product_name'):
            product.product_name = data['product_name']
            updated_fields.append('product_name')
            
        if data.get('selling_price'):
            product.selling_price = data['selling_price']
            updated_fields.append('selling_price')
            
        if data.get('initial_stock') is not None:  # Allow 0 as valid value
            product.initial_stock = data['initial_stock']
            updated_fields.append('initial_stock')
            
        if data.get('expiration_date'):
            product.expiration_date = data['expiration_date']
            updated_fields.append('expiration_date')
            
        if data.get('supplier_info'):
            product.supplier_info = data['supplier_info']
            updated_fields.append('supplier_info')
        
        if not updated_fields:
            return jsonify({"message": "No valid fields provided for update"}), 400
        
        db.session.commit()
        
        return jsonify({
            "message": "Product updated successfully",
            "updated_fields": updated_fields,
            "product": {
                "id": product.id,
                "product_name": product.product_name,
                "selling_price": product.selling_price,
                "initial_stock": product.initial_stock,
                "expiration_date": product.expiration_date,
                "supplier_info": product.supplier_info
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Update failed: {str(e)}"}), 500