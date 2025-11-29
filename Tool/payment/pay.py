from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import User, Payment
from app.db import db 
from datetime import datetime, timedelta
import requests
import hmac, hashlib
import os
from decimal import Decimal




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

    paystack_amount = int(float(amount)* 100)


    # Create a new Payment record
    reference = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"
    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        reference=reference,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.session.add(payment)
    db.session.commit()


    # Initialize payment with Paystack
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
        "Content-Type": "application/json"

    }
    payload = {
        "email": current_user.email,
        "amount": paystack_amount,
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
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "User not found"}), 404

    # Find existing payment
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        return jsonify({"message": "Payment not found"}), 404

    # Check Paystack status (but don't update database yet)
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        verification_data = response.json()
    except requests.exceptions.RequestException:
        return jsonify({"message": "Error verifying transaction"}), 500

    paystack_data = verification_data.get("data", {})
    paystack_status = paystack_data.get("status")
    amount_paid = float(paystack_data.get("amount", 0)) / 100
    
    if paystack_status == "success":
        
        return jsonify({
            "message": "Payment verified successfully! Balance will be updated shortly.",
            "paystack_status": paystack_status,  
            "payment_status": payment.status,   
            "amount": amount_paid,
            "current_balance": round(float(current_user.balance or 0), 2)
        }), 200
    else:
        return jsonify({
            "message": "Payment verification failed",
            "status": paystack_status
        }), 400




#paystack webhook
@payment.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    """
    Handles Paystack payment webhooks securely and updates payment status.
    """
    try:
        # Verify Paystack signature
        paystack_signature = request.headers.get("x-paystack-signature")
        body = request.get_data()

        if not paystack_signature:
            return jsonify({
                "status": "error", 
                "message": "Missing signature"
            }), 400

        secret = os.getenv("PAYSTACK_SECRET_KEY", "").encode()
        computed_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()

        if computed_signature != paystack_signature:
            return jsonify({"status": "error", "message": "Invalid signature"}), 400

        # Parse JSON payload
        event = request.get_json(silent=True)
        if not event:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        event_type = event.get("event")
        data = event.get("data", {})
        reference = data.get("reference")

        # Process relevant events
        if event_type == "charge.success":
            if not reference:
                return jsonify({"status": "error", "message": "Missing reference"}), 400

            payment = Payment.query.filter_by(reference=reference).first()
            if not payment:
                return jsonify({
                    "status": "error",
                    "message": f"No Payment record found for reference: {reference}"
                }), 404

            # FIXED: Prevent duplicate processing
            if payment.status == "success":
                return jsonify({"status": "success", "message": "Already processed"}), 200

            # FIXED: Extract amount from webhook data
            amount_paid = float(data.get("amount", 0)) / 100  # Convert pesewas to GHS

            # FIXED: Update payment record
            payment.status = "success"
            payment.amount = amount_paid

            #FIXED: Update user balance
            user = User.query.get(payment.user_id)
            if user:
                current_balance = float(user.balance or 0)
                user.balance = round(current_balance + amount_paid, 2)

            db.session.commit()

            return jsonify({
                "status": "success",
                "message": "Payment processed",
                "amount_added": amount_paid
            }), 200

        elif event_type == "charge.failed":
            if reference:
                payment = Payment.query.filter_by(reference=reference).first()
                if payment and payment.status != "failed":
                    payment.status = "failed"
                    db.session.commit()

        # Always respond 200 to acknowledge receipt
        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500