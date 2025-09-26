from flask import request, Blueprint, jsonify
from app.models import db, User, Product
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
        if Missing_fields:
            return jsonify({"message":
            f"{Missing_fields} required"
        }), 400

    save_pro = Product(
        product_name=product_name,
        selling_price=selling_price,
        initial_stock=initial_stock,
        remaining_stock=initial_stock,
        expiration_date=expiration_date,
        supplier_info=supplier_info,
        user_id=current_user.id
    )
    db.session.add(save_pro)
    db.session.commit()
    return jsonify({"message":
        "product information saves successfully"
                    
        }), 200





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

        product = Product.query.get_or_404(product_id)
        if product.user_id != current_user.id:
            return jsonify({"message":
            "Unauthorized "
        }), 403

        # Archiving the product
        product.status = 'archived'
        product.archived_at = datetime.utcnow()

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

        # Get search input from query string: /product/filter?name=keysoap
        search_name = request.args.get("name")
        if not search_name:
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
                product_data["archived_at"] = product.archived_at.isoformat()
            
            products_list.append(product_data)
        
        return jsonify({
            "products": products_list,
            "total": len(products_list),
            "status_filter": status
        }), 200
        
    except Exception as e:
        return jsonify({"message":
         f"Error: {str(e)}"}), 500