from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import db, User, Payment
from datetime import datetime, timedelta
import requests
import hmac, hashlib
import os




payment = Blueprint('payment', __name__)


@payment.route('/initialize-payment', methods=['POST'])
@jwt_required()
def initialize_payment():
    
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()
    if not current_user:
        return jsonify({"message":
             "user not found"}), 400


    data = request.get_json()
    amount = data.get("amount")  
    email = data.get("email")
    
    if not amount and not email:
        return jsonify({"message":
             "amount and email required"}), 400

    # Create a new Payment record
    reference = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"
    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        reference=reference,
        status="pending",
        created_at=datetime.utcnow(),
        expiry_date=datetime.utcnow() + timedelta(days=30)
    )
    
    db.session.add(payment)
    db.session.commit()


    # Initialize payment with Paystack
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
        "Content-Type": "application/json"

    }
    PREMIUM_PRICE = 3000
    payload = {
        "email": current_user.email,
        "amount": PREMIUM_PRICE,
        "currency": "GHS", 
        "reference": reference
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        paystack_response = response.json()
    except requests.exceptions.RequestException:
        return jsonify({"Error": "error initializing transaction"}), 500
    except ValueError:
        return jsonify({"Error": "Invalid JSON response from paystack"}), 500

    # Save gateway response
    payment.gateway_response = str(paystack_response)
    db.session.commit()

    return jsonify(paystack_response)

#VERIFYING PAYMENTS
@payment.route('/verify_payment/<reference>', methods=['GET'])
@jwt_required()
def verify_payment(reference):

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers ={
    "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        verification_data = response.json()
    except requests.exceptions.RequestException:
        return jsonify({"message": "Error verifying transaction"}), 500
    except ValueError:
        return jsonify({"message": "Invalid response from paystack"}), 500
    
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        return jsonify({"message": "payment not found"}), 404
    
    if verification_data["data"]["status"] == "success":
        payment.status = "success"
    
    else:
        payment.status = "failed"
    
    db.session.commit()
    return jsonify(verification_data)


#paystack webhook
@payment.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    # Verify signature
    paystack_signature = request.headers.get("x-paystack-signature")
    body = request.get_data()

    secret = os.getenv("PAYSTACK_SECRET_KEY").encode()
    computer_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()

    if computer_signature != paystack_signature:
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

    event = request.get_json()

    if event["event"] == "charge.success":
        reference = event["data"]["reference"]
        # update your Payment record
        payment = Payment.query.filter_by(reference=reference).first()
        if payment:
            payment.status = "success"
            db.session.commit()

    return jsonify({"status": "success"}), 200

