from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import User, Payment
from app.db import db 
from datetime import datetime
import requests
import hmac, hashlib
import os
from decimal import Decimal
from app.db import app_logger


payment = Blueprint('payment', __name__)


# SMS Bundle Configuration - Users get EXACT amounts, no leftovers
SMS_BUNDLES = {
    "small": {
        "sms_credits": 500,
        "sell_price": 20.00,
        "cost": 15.50,
        "profit": 4.50,
        "profit_margin": "22%",
        "packs_needed": 1,
        "leftover_units": 145  # Tracked but NOT given to user
    },
    "medium": {
        "sms_credits": 1000,
        "sell_price": 40.00,
        "cost": 31.00,
        "profit": 9.00,
        "profit_margin": "22%",
        "packs_needed": 2,
        "leftover_units": 290
    },
    "large": {
        "sms_credits": 5000,
        "sell_price": 200.00,
        "cost": 155.00,
        "profit": 45.00,
        "profit_margin": "22%",
        "packs_needed": 8,
        "leftover_units": 160
    },
    "xl": {
        "sms_credits": 10000,
        "sell_price": 400.00,
        "cost": 310.00,
        "profit": 90.00,
        "profit_margin": "22%",
        "packs_needed": 16,
        "leftover_units": 320
    }
}




@payment.route('/get-bundles', methods=['GET'])
def get_bundles():
    """Return available SMS bundles for frontend display"""
    app_logger.payment_plans_attempt("sms plans attempted retrival")
    bundles = []
    for bundle_id, details in SMS_BUNDLES.items():
        bundles.append({
            "id": bundle_id,
            "name": bundle_id.capitalize(),
            "sms_credits": details["sms_credits"],
            "price": details["sell_price"],
            "price_per_sms": round(details["sell_price"] / details["sms_credits"], 4)
        })
    
    app_logger.payment_plans_success("sms plans retrieved successfully")
    return jsonify({"bundles": bundles}), 200


@payment.route('/initialize-payment', methods=['POST'])
@jwt_required()
def initialize_payment():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()
    
    if not current_user:
        return jsonify({"message": "User not found"}), 400

    app_logger.payment_paying_attempt(current_user, request.remote_addr)


    data = request.get_json()
    bundle_type = data.get("bundle_type")  # Changed from amount to bundle_type
    
    if not bundle_type or bundle_type not in SMS_BUNDLES:
        app_logger.payment_paying_failure(current_user, reason="missing plan choice")
        return jsonify({
            "message": "Invalid bundle type. Choose: small, medium, large, or xl"
        }), 400

    # Get bundle details
    bundle = SMS_BUNDLES[bundle_type]
    amount = bundle["sell_price"]
    sms_credits = bundle["sms_credits"]
    
    # Convert to pesewas for Paystack
    paystack_amount = int(float(amount) * 100)

    # Create payment record with bundle info
    reference = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"
    new_payment = Payment(
        user_id=current_user.id,
        amount=amount,
        reference=reference,
        status="pending",
        created_at=datetime.utcnow(),
        bundle_type=bundle_type  # Store bundle type directly
    )
    
    db.session.add(new_payment)
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
        "reference": reference,
        "metadata": {
            "bundle_type": bundle_type,
            "sms_credits": sms_credits
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        paystack_response = response.json()
        
        # Save gateway response
        new_payment.gateway_response = str(paystack_response)
        db.session.commit()
        
        app_logger.payment_paying_success(current_user)

        return jsonify({
            "status": "success",
            "bundle": {
                "type": bundle_type,
                "sms_credits": sms_credits,
                "price": amount
            },
            "paystack_data": paystack_response
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Error initializing transaction"}), 500


@payment.route('/verify_payment/<reference>', methods=['GET'])
@jwt_required()
def verify_payment(reference):
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "User not found"}), 404

    app_logger.payment_verification_attempt(current_user, request.remote_addr)



    payment_record = Payment.query.filter_by(reference=reference).first()
    if not payment_record:
        return jsonify({"message": "Payment not found"}), 404

    # Verify with Paystack
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
    
    app_logger.payment_verification_success(current_user)

    if paystack_status == "success":
        return jsonify({
            "message": "Payment verified successfully!",
            "paystack_status": paystack_status,
            "payment_status": payment_record.status,
            "amount": amount_paid,
            "current_sms_balance": int(current_user.sms_balance or 0)
        }), 200
    else:
        app_logger.payment_verification_failure(current_user, reason="failed")
        return jsonify({
            "message": "Payment verification failed",
            "status": paystack_status
        }), 400


@payment.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    """
    Handles Paystack webhooks and credits EXACT SMS amounts (no leftovers)
    """
    try:
        # Verify Paystack signature
        paystack_signature = request.headers.get("x-paystack-signature")
        body = request.get_data()

        if not paystack_signature:
            return jsonify({"status": "error", "message": "Missing signature"}), 400


        app_logger.payment_webhook_attempt("paystack tried calling webhook")

        secret = os.getenv("PAYSTACK_SECRET_KEY", "").encode()
        computed_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()

        if computed_signature != paystack_signature:
            return jsonify({"status": "error", "message": "Invalid signature"}), 400

        event = request.get_json(silent=True)
        if not event:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        event_type = event.get("event")
        data = event.get("data", {})
        reference = data.get("reference")

        if event_type == "charge.success":
            if not reference:
                return jsonify({"status": "error", "message": "Missing reference"}), 400

            payment_record = Payment.query.filter_by(reference=reference).first()
            if not payment_record:
                app_logger.payment_webhook_failure("webhook calling failed")
                return jsonify({"status": "error", "message": "Payment not found"}), 404

            # Prevent duplicate processing
            if payment_record.status == "success":
                return jsonify({"status": "success", "message": "Already processed"}), 200

            # Get bundle type from payment record
            bundle_type = payment_record.bundle_type
            
            if not bundle_type or bundle_type not in SMS_BUNDLES:
                return jsonify({"status": "error", "message": "Invalid bundle"}), 400

            bundle = SMS_BUNDLES[bundle_type]
            amount_paid = float(data.get("amount", 0)) / 100
            
            # Verify amount matches expected price
            if abs(amount_paid - bundle["sell_price"]) > 0.01:
                return jsonify({"status": "error", "message": "Amount mismatch"}), 400

            # Update payment record
            payment_record.status = "success"
            payment_record.amount = amount_paid

            # Credit user with EXACT SMS amount (NO leftovers)
            user = User.query.get(payment_record.user_id)
            if user:
                current_sms_balance = int(user.sms_balance or 0)
                user.sms_balance = current_sms_balance + bundle["sms_credits"]
                
                # Optional: Track your costs and leftovers separately
                # (This is for your accounting, not given to user)
                # You can add these fields to track business metrics

           
            db.session.commit()

            
           
           
            app_logger.payment_webhook_success("webhook called successfully")


            return jsonify({
                "status": "success",
                "message": "Payment processed",
                "sms_credited": bundle["sms_credits"],
                "amount_paid": amount_paid
            }), 200

        elif event_type == "charge.failed":
            if reference:
                payment_record = Payment.query.filter_by(reference=reference).first()
                if payment_record and payment_record.status != "failed":
                    payment_record.status = "failed"
                    db.session.commit()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500