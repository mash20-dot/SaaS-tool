from flask import jsonify, Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Store, db
from slugify import slugify

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


