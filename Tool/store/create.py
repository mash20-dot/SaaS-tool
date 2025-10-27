from flask import jsonify, Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Store, db, Store_product
from slugify import slugify
from urllib.parse import quote_plus

store = Blueprint("store", "__name__")


def generate_slug(text, max_length=120):
    # slugify handles accents, punctuation, etc.
    s = slugify(text)[:max_length].strip('-')
    return s or 'store'  # fallback if slug is empty

def create_unique_slug(store_name):
    base_slug = generate_slug(store_name)
    slug = base_slug
    counter = 1

    # Query DB to check existence
    while db.session.query(Store).filter_by(slug=slug).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug



@store.route('/create', methods=['POST'])
@jwt_required()
def create():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message":"user not found"
        })

    data = request.get_json()
    store_name = data.get("store_name")
    whatsapp_business_number = data.get("whatsapp_business_number")
    logo_url = data.get("logo_url")
    cover_url = data.get("cover_url")
    description = data.get("description")

    Missing_fields = []

    if not store_name:
        Missing_fields.append("store_name")
    if not whatsapp_business_number:
        Missing_fields.append("whatsapp_business_number")
        if Missing_fields:
            return jsonify({
                "message": f"{Missing_fields} required"
            }), 400
    
    slug = create_unique_slug(store_name)

    new_store = Store(
        user_id = current_user.id,
        store_name=store_name,
        slug=slug,
        whatsapp_business_number=whatsapp_business_number,
        logo_url=logo_url,
        cover_url=cover_url,
        description=description,
        is_active=True
    )

    db.session.add(new_store)
    db.session.commit()

    BASE_DOMAIN = "https://nkwabiz.com"
    BASE_DOMAIN_TEST = "http://localhost:5000"

    full_url = f"{BASE_DOMAIN_TEST}/store/{slug}"

    return jsonify({
        "message": "store created successfully",
        "slug": slug,
        "full_url": full_url
    }), 201


@store.route('/product', methods=['POST'])
@jwt_required()
def product():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message":"user not found"
        }), 400
    
    data = request.get_json()
    product_name = data.get("product_name")
    description = data.get("description")
    logo_url = data.get("logo_url")
    amount = data.get("amount")

    Missing_fields = []
    if not product_name:
        Missing_fields.append("product_name")
    if not amount:
        Missing_fields.append("amount")
        if Missing_fields:
            return jsonify({
                "message": f"{Missing_fields} required"
            }), 400
    
    #store_id = Store.query.filter_by(
        #user_id=current_user.id
    #)
    store_id = db.session.query(Store.id).filter_by(
        user_id=current_user.id).scalar()
    
    new_product = Store_product(
        store_id=store_id,
        user_id=current_user.id,
        product_name=product_name,
        description=description,
        logo_url=logo_url,
        amount=float(amount)

    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify({
        "message":"product added successfully"
        }),201


@store.route('/update/<int:product_id>', methods=['PUT'])
@jwt_required()
def update(product_id):

    try:

        current_email = get_jwt_identity()
        current_user = User.query.filter_by(
            email=current_email
            ).first()
        
        if not current_user:
            return jsonify({
                "message":"user not found"
            }), 400
        
        product = Store_product.query.get_or_404(product_id)


            
            
        if product.user_id != current_user.id:
                return jsonify({"message":
            "Unauthorized to edit this product"}), 403
        
        data = request.get_json()
        update_fields = []

        if data.get("product_name"):
            product.product_name = data["product_name"]
            update_fields.append("product_name")

        if data.get("description"):
            product.description = data["description"]
            update_fields.append("description")
        
        if data.get("logo_url"):
            product.logo_url = data["logo_url"]
            update_fields.append("logo_url")
        
        if data.get("amount"):
            product.amount = data["amount"]
            update_fields.append("amount")
        
        if not update_fields:
            return jsonify({
                "message":"No valid field provided for update"
            }), 400
        
        db.session.commit()

        return jsonify({
            "message":"product upated successfully",
            "updated_fields":update_fields,
            "product":{
                "product_name":product.product_name,
                "description":product.description,
                "logo_url":product.logo_url,
                "amount":float(product.amount)
            }

        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": f"update failed {str(e)}"
        }), 500
    
    #NOW TEST THIS

#helper function to generate whatsapp link for users
def make_whatsapp_link(phone, message=None):
    phone = str(phone).replace("+", "").replace(" ", "")
    if message:
        return f"https://wa.me/{phone}?text={quote_plus(message)}"
    return f"https://wa.me/{phone}"


@store.route("/api/wa-link", methods=["GET"])
def api_wa_link():
    try:
        user_id = request.args.get("user_id", type=int)
        store_id = request.args.get("store_id")
        if not user_id:
            return jsonify({"status":
                    "error", "message": "user_id is required"
                }), 400

        # Fetch the user from your database
        user = Store.query.get(user_id)
        if not user or not user.whatsapp_business_number:
            return jsonify({"status": 
                            "error", "message": "User not found or phone number missing"
                }), 404

        pro = Store_product.get(store_id)

        # Generate link dynamically from user's phone
        message = request.args.get(
            pro.description)
        wa_link = make_whatsapp_link(user.whatsapp_business_number, message)

        return jsonify({
            "status": "success",
            "user": user.user_id,
            "whatsapp_link": wa_link
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
