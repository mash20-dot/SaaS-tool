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
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message": "User not found"}), 404

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
    except ValueError:
        return jsonify({"message": "Invalid response from Paystack"}), 500

    # Find existing payment
    payment = Payment.query.filter_by(
        reference=reference).first()
    if not payment:
        return jsonify({"message":
             "Payment not found"}), 404

    # Prevent reprocessing
    if payment.status == "success":
        return jsonify({"message":
             "Payment already processed"}), 200

    # Extract Paystack data
    paystack_data = verification_data.get("data", {})
    if paystack_data.get("status") == "success":
        # Convert pesewas to GHS
        amount_paid = float(paystack_data["amount"]) / 100

        # Update payment status & amount
        payment.status = "success"
        payment.amount = amount_paid

        # Update user balance
        current_user.balance = float(current_user.balance or 0) + float(amount_paid)

        db.session.commit()

        return jsonify({
            "message": "Payment verified successfully",
            "amount_added": amount_paid,
            "new_balance": round(current_user.balance, 2),
            "verification": verification_data
        }), 200

    else:
        payment.status = "failed"
        db.session.commit()
        return jsonify({"message": "Payment failed"}), 400



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
                "status":
                  "error", 
                  "message": "Missing signature"}), 400

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
            if payment:
                if payment.status != "success":
                    payment.status = "success"
                    db.session.commit()
            else:
                return jsonify({
                    f"No Payment record found for reference: {reference}"}), 404

        elif event_type == "charge.failed":
            if reference:
                payment = Payment.query.filter_by(reference=reference).first()
                if payment:
                    payment.status = "failed"
                    db.session.commit()

        # Always respond 200 to acknowledge receipt
        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500