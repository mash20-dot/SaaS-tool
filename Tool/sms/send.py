from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
from app.models import User, db
import os
from datetime import datetime

sms = Blueprint("sms", "__name__")

cost_per_sms = float("0.15")

@sms.route('/api/sms/send', methods=['POST'])
@jwt_required()
def send():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400

    # Check if user has enough balance
    user_balance = float(current_user.balance or 0)
    if user_balance < cost_per_sms:
        return jsonify({
            "message": 
            "Your balance is too low to send an SMS. Please top up."
        }), 403

    # Get SMS details from request body
    data = request.get_json()
    recipient = data.get("recipient")
    message = data.get("message")

    if not recipient or not message:
        return jsonify({"error":
                 "recipient and message are required"}), 400

    sender_name = current_user.business_name


    url = "https://sms.arkesel.com/api/v2/sms/send"
    payload = {
        "sender": sender_name,
        "message": message,
        "recipients": [recipient]
    }

    key = os.getenv("ARKESEL_SMS_KEY")
    headers = {
        "api-key": key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        # Check if SMS was sent successfully
        if response.status_code == 200 and response_data.get("status") == "success":
            # Deduct the cost from user balance
            current_user.balance = user_balance - cost_per_sms
            db.session.commit()

            return jsonify({
                "message": "SMS sent successfully",
                "new_balance": float(current_user.balance),
                "cost_deducted": float(cost_per_sms),
                "arkesel_response": response_data
            }), 200
        else:
            return jsonify({
                "error": "Failed to send SMS",
                "arkesel_response": response_data
            }), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500
