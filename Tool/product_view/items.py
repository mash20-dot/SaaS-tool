from flask import request, Blueprint, jsonify
from app.models import User, Product, Payment
from app.db import db , app_logger
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required


product_view = Blueprint('product_view', '__name__')

#route to post products
@product_view.route('/product/post_product', methods=['POST'])
@jwt_required()
def start():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
                 "user not found"}), 400

    data = request.get_json()

    try:
        product_name = data.get("product_name")
        selling_price = data.get("selling_price")
        amount_spent = data.get("amount_spent")
        initial_stock = data.get("initial_stock")
        expiration_date = data.get("expiration_date")
        supplier_info = data.get("supplier_info")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid data type for one or more fields"}), 400

    #post attemp
    app_logger.product_attempt(current_user, request.remote_addr)


    # Validation
    missing_fields = [f for f in ["product_name", "selling_price", "initial_stock", "amount_spent"] if not data.get(f)]
    if missing_fields:
        app_logger.product_failure(current_user, reason="missing fields")
        return jsonify({"message": f"{missing_fields} required"}), 400
    


    save_pro = Product(
        product_name=product_name,
        selling_price=selling_price,
        amount_spent=amount_spent, 
        initial_stock=initial_stock,
        remaining_stock=initial_stock,
        expiration_date=expiration_date,
        supplier_info=supplier_info,
        user_id=current_user.id
    )

    app_logger.product_success(current_email)

    db.session.add(save_pro)
    db.session.commit()

    return jsonify({"message":
             "product information saved successfully"}), 200

#route to update product        
@product_view.route('/product/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        current_user_email = get_jwt_identity()
        current_user = User.query.filter_by(
            email=current_user_email).first()
        
        if not current_user:
            return jsonify({"message":
                 "User not found"}), 404
        
       
        
        product = Product.query.get_or_404(product_id)

        app_logger.product_update_attempt(current_user, request.remote_addr)
        
        
        if product.user_id != current_user.id:
            return jsonify({"message":
         "Unauthorized to edit this product"}), 403
        
        
        data = request.get_json()
        updated_fields = []
        
        # Only update fields that are actually provided and not empty
        if data.get('product_name'):
            product.product_name = data['product_name']
            updated_fields.append('product_name')
            
        if data.get('selling_price'):
            product.selling_price = data['selling_price']
            updated_fields.append('selling_price')
        
        if data.get('amount_spent'):
            product.amount_spent = data['amount_spent']
            updated_fields.append('amount_spent')
            

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
            app_logger.product_failure(current_user, reason="missinf fields")
            return jsonify({"message": "No valid fields provided for update"}), 400
        
        app_logger.product_success(current_user)

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


#route to achive a product
@product_view.route('/product/<int:product_id>/archive', methods=['POST'])
@jwt_required()
def archive(product_id):

    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_email).first()

        if not current_user:
            return jsonify({"message":
                "user not found"
        }), 400

        app_logger.product_archive_attempt(current_user, request.remote_addr)

        premium = Payment.query.filter_by(
        user_id=current_user.id, status="success"
        ).order_by(Payment.created_at.desc()).first()

        if not premium:
            return jsonify({"message":
            "You do not have a premium subscription. Please upgrade."
            }), 403
        
        if premium.expiry_date < datetime.utcnow():
            return jsonify({"message": 
            "Your premium has expired. Please renew."}), 403


        product = Product.query.get_or_404(product_id)
        if product.user_id != current_user.id:
            app_logger.product_archive_failure(current_user, reason="unauthorized")
            return jsonify({"message":
            "Unauthorized "
        }), 403

        # Archiving the product
        product.status = 'archived'
        product.archived_at = datetime.utcnow()

        app_logger.product_archive_success(current_user)

        db.session.commit()
        return jsonify({"message":
                        
            "product archived successfully",
            "archived_at": product.archived_at.isoformat()
                
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message":
            f"product could not be archived {str(e)}"
            }), 500

#search for product by name
@product_view.route('/product/filter', methods=['GET'])
@jwt_required()
def filter_products():
    try:
        # Identify the user
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(
            email=current_email).first()
        if not current_user:
            return jsonify({"message":
                 "user not found"}), 400
        
        app_logger.product_search_attempt(current_user, request.remote_addr)

        # Get search input from query string: /product/filter?name=keysoap
        search_name = request.args.get("name")
        if not search_name:
            app_logger.product_search_failure(current_user, reason="missing field")
            return jsonify({"message":
             "product name is required"}), 400

        # Filter products by name (case-insensitive) + only this user
        products = Product.query.filter(
            Product.user_id == current_user.id,
            Product.product_name.ilike(f"%{search_name}%")
        ).all()

        if not products:
            return jsonify({"message":
             "no matching products found"}), 404
        
        app_logger.product_search_success(current_user)

        # Return matching products
        return jsonify([
            {
                "product_name": p.product_name,
                "selling_price": p.selling_price,
                "initial_stock": p.initial_stock,
                "expiration_date": p.expiration_date,
                "supplier_info": p.supplier_info,
                "status": p.status
            }
            for p in products
        ]), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message":
                 f"could not filter product: {str(e)}"
                 }), 500

#route to get product based on the status         
@product_view.route('/product', methods=['GET'])
@jwt_required()
def get_products():
    try:
        current_user_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_user_email).first()
        
        if not current_user:
            return jsonify({"message": "User not found"}), 404
        
        app_logger.product_status_attempt(current_user, request.remote_addr)
        
        # Get status filter from query params, default=active
        status = request.args.get('status', 'active') 
        
        if status == 'all':
            products = Product.query.filter_by(user_id=current_user.id).all()
        else:
            products = Product.query.filter_by(user_id=current_user.id, status=status).all()
        
        products_list = []
        for product in products:
            product_data = {
                "id": product.id,
                "product_name": product.product_name,
                "selling_price": product.selling_price,
                "initial_stock": product.initial_stock,
                "expiration_date": product.expiration_date,
                "supplier_info": product.supplier_info,
                "status": product.status
            }
            
            if product.archived_at:
                #app_logger.product_status_failure(current_user)
                product_data["archived_at"] = product.archived_at.isoformat()
            
            products_list.append(product_data)
        
        app_logger.product_status_success(current_user)
        
        return jsonify({
            "products": products_list,
            "total": len(products_list),
            "status_filter": status
        }), 200
        
    except Exception as e:
        return jsonify({"message":
         f"Error: {str(e)}"}), 500



